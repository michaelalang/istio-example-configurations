# Istio Example Configurations

This repository contains a collection of example configurations demonstrating various use cases and features of Istio Service Mesh.

## Use Case Summaries

### Coraza WAF at the Gateway
In this scenario, we apply a `WasmPlugin` with the Coraza WAF image to the Istio gateway. The WAF is configured with a set of rules to inspect incoming requests and deny them if they match certain criteria, such as specific URIs, user-agents, or IP addresses in the `x-forwarded-for` header.

### Istio with OpenShift DeploymentConfig
This example shows a simple `httpd` application deployed using an OpenShift `DeploymentConfig`. The key aspect of this use case is to illustrate how the Istio sidecar is injected into the `DeploymentConfig`'s pod template, demonstrating compatibility with OpenShift-specific resources.

### Egress Database Connectivity
This scenario addresses the common requirement of securely connecting to an external database from within the service mesh. It uses `ServiceEntry`, an egress gateway, `VirtualService`, `DestinationRule`, and `AuthorizationPolicy` to control and secure egress traffic to an external PostgreSQL database.

### External Authorization with OAuth2-Proxy and Dex
This scenario provides a complete example of how to secure your service mesh with a robust authentication and authorization solution. It integrates `oauth2-proxy` as an external authorization service with Istio's `ext_authz` mechanism, using Dex as the OpenID Connect (OIDC) provider.

### Egress Traffic through an External Proxy
This scenario addresses the common requirement of routing all outbound traffic through a central proxy for security, monitoring, or policy enforcement purposes. It presents two approaches: using an Istio egress gateway and a transparent proxy, both routing traffic through a Squid proxy.

### Gateway TLS Configuration: Passthrough vs. Re-encryption
This scenario provides a practical comparison of two common TLS configurations at the gateway: TLS passthrough (where the gateway forwards encrypted traffic directly to the backend) and TLS re-encryption (where the gateway terminates TLS from the client and re-encrypts to the backend using the service CA).

### Kubernetes Gateway API vs. Istio Gateway
This example demonstrates how to achieve the same result—exposing an HTTP service—using two different sets of APIs: the new Kubernetes Gateway API and the traditional Istio Gateway. It's useful for understanding the differences and potential migration paths.

### Remove Server Headers from HTTP Response
For security and information hiding purposes, it's often desirable to remove certain headers from the HTTP response. This example uses `EnvoyFilter` to remove headers like `server`, `x-envoy-upstream-service-time`, and `x-powered-by` from responses at both the gateway and sidecar.

### Restrict Access to Specific Paths
This example provides a comparison of three different methods for controlling access to specific URL paths: using an `AuthorizationPolicy`, an `EnvoyFilter` with a Lua script, and a `VirtualService` with `directResponse`. Each method offers different trade-offs in complexity and flexibility.

### Sidecar Memory Consumption
This use case is designed to demonstrate how the size and complexity of the Istio configuration can impact the memory consumption of the sidecar proxies. It uses a very large `VirtualService` to illustrate the direct relationship between configuration size and sidecar memory usage.

### Soft Multi-Tenancy with a Shared Gateway
This scenario provides a simple example of how to achieve multi-tenancy in Istio without requiring a separate gateway for each tenant. It uses a shared Istio gateway, separate tenant namespaces, and tenant-specific `VirtualService` configurations to balance isolation and resource utilization.
