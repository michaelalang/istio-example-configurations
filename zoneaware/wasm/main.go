package main

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/tetratelabs/proxy-wasm-go-sdk/proxywasm"
	"github.com/tetratelabs/proxy-wasm-go-sdk/proxywasm/types"
)

// Metric names
const (
	MetricAllowed = "http_filter_allowed_requests"
	MetricBlocked = "http_filter_blocked_requests"
)

func main() {
	proxywasm.SetVMContext(&vmContext{})
}

// vmContext implements the VM lifecycle
type vmContext struct {
	types.DefaultVMContext
}

func (*vmContext) NewPluginContext(contextID uint32) types.PluginContext {
	return &pluginContext{
		waitingContexts: make(map[uint32]int64),
	}
}

// pluginContext handles the plugin configuration
type pluginContext struct {
	types.DefaultPluginContext
	config          PolicyConfig
	metricAllow     proxywasm.MetricCounter
	metricBlock     proxywasm.MetricCounter
	waitingContexts map[uint32]int64
}

// PolicyConfig defines the JSON configuration structure
type PolicyConfig struct {
	AllowMissingIdentity   bool              `json:"allow_missing_identity"`
	AllowedNamespaces      []string          `json:"allowed_namespaces"`
	AllowedServiceAccounts []string          `json:"allowed_service_accounts"`
	Delays                 map[string]uint32 `json:"delays"` // Map of SA -> Delay in ms
}

func (ctx *pluginContext) OnPluginStart(pluginConfigurationSize int) types.OnPluginStartStatus {
	data, err := proxywasm.GetPluginConfiguration()
	if err != nil {
		proxywasm.LogCriticalf("Error loading config: %v", err)
		return types.OnPluginStartStatusFailed
	}

	if len(data) > 0 {
		if err := json.Unmarshal(data, &ctx.config); err != nil {
			proxywasm.LogCriticalf("Error parsing config: %v", err)
			return types.OnPluginStartStatusFailed
		}
	}

	ctx.metricAllow = proxywasm.DefineCounterMetric(MetricAllowed)
	ctx.metricBlock = proxywasm.DefineCounterMetric(MetricBlocked)

	return types.OnPluginStartStatusOK
}

// OnTick handles the resumption of paused HTTP requests after their delay
func (ctx *pluginContext) OnTick() {
	now := time.Now().UnixMilli()
	for contextID, expireAt := range ctx.waitingContexts {
		if now >= expireAt {
			delete(ctx.waitingContexts, contextID)
			proxywasm.LogInfof("Resuming HTTP request after delay (context %d)", contextID)
			if err := proxywasm.SetEffectiveContext(contextID); err != nil {
				proxywasm.LogCriticalf("Failed to set effective context: %v", err)
				continue
			}
			if err := proxywasm.ResumeHttpRequest(); err != nil {
				proxywasm.LogCriticalf("Failed to resume HTTP request: %v", err)
			}
		}
	}
	if len(ctx.waitingContexts) == 0 {
		proxywasm.SetTickPeriodMilliSeconds(0) // Stop ticking when no connections are waiting
	}
}

func (ctx *pluginContext) NewHttpContext(contextID uint32) types.HttpContext {
	return &httpContext{
		parent:    ctx,
		contextID: contextID,
	}
}

// httpContext handles individual HTTP requests
type httpContext struct {
	types.DefaultHttpContext
	parent    *pluginContext
	contextID uint32
}

// OnHttpRequestHeaders checks the Downstream Principal (mTLS Identity)
func (ctx *httpContext) OnHttpRequestHeaders(numHeaders int, endOfStream bool) types.Action {
	// First, perform the access check and extract the Service Account (sa)
	action, sa := ctx.checkAccess()

	// If access is granted, check if a delay is configured for this specific SA
	if action == types.ActionContinue {
		delay := ctx.parent.config.Delays[sa]
		
		// Log the findings as requested
		logSA := sa
		if logSA == "" {
			logSA = "[None/Missing]"
		}
		proxywasm.LogWarnf("Request from SA: %s. Delay applied: %d ms (context %d)", logSA, delay, ctx.contextID)

		if delay > 0 {
			now := time.Now().UnixMilli()
			expireAt := now + int64(delay)
			ctx.parent.waitingContexts[ctx.contextID] = expireAt
			
			// Ensure the tick timer is running (resolution of 10ms)
			proxywasm.SetTickPeriodMilliSeconds(10)
			return types.ActionPause
		}
	}

	return action
}

func (ctx *httpContext) checkAccess() (types.Action, string) {
	// Retrieve the URI SAN from the peer certificate
	rawID, err := proxywasm.GetProperty([]string{"connection", "uri_san_peer_certificate"})

	// Handle cases where mTLS is not used or ID is missing
	if err != nil || len(rawID) == 0 {
		if ctx.parent.config.AllowMissingIdentity {
			ctx.allow("Missing Identity (Allowed by config)")
			return types.ActionContinue, ""
		}
		ctx.block("Missing Identity")
		return types.ActionPause, ""
	}

	spiffeID := string(rawID)
	ns, sa := parseSpiffeID(spiffeID)

	if ns == "" || sa == "" {
		ctx.block("Invalid SPIFFE format: " + spiffeID)
		return types.ActionPause, ""
	}

	if !isAllowed(ctx.parent.config.AllowedNamespaces, ns) {
		ctx.block("Namespace denied: " + ns)
		return types.ActionPause, ""
	}

	if !isAllowed(ctx.parent.config.AllowedServiceAccounts, sa) {
		ctx.block("ServiceAccount denied: " + sa)
		return types.ActionPause, ""
	}

	ctx.allow("Access Granted: " + spiffeID)
	return types.ActionContinue, sa
}

func isAllowed(allowedList []string, value string) bool {
	for _, item := range allowedList {
		if item == "*" || item == value {
			return true
		}
	}
	return false
}

func parseSpiffeID(id string) (namespace string, serviceAccount string) {
	const nsMarker = "/ns/"
	const saMarker = "/sa/"

	nsIndex := strings.Index(id, nsMarker)
	if nsIndex == -1 {
		return "", ""
	}

	remaining := id[nsIndex+len(nsMarker):]
	saIndex := strings.Index(remaining, saMarker)
	if saIndex == -1 {
		return "", ""
	}

	namespace = remaining[:saIndex]
	serviceAccount = remaining[saIndex+len(saMarker):]

	return namespace, serviceAccount
}

func (ctx *httpContext) block(reason string) {
	ctx.parent.metricBlock.Increment(1)
	proxywasm.LogWarnf("[HTTP Filter] BLOCKED request. Reason: %s", reason)
	
	// Reject the HTTP request gracefully
	if err := proxywasm.SendHttpResponse(403, [][2]string{{"content-type", "text/plain"}}, []byte("Access Denied: "+reason), -1); err != nil {
		proxywasm.LogErrorf("failed to send local response: %v", err)
	}
}

func (ctx *httpContext) allow(reason string) {
	ctx.parent.metricAllow.Increment(1)
	proxywasm.LogDebugf("[HTTP Filter] ALLOWED request. %s", reason)
}
