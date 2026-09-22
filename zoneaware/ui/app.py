import asyncio
import time
import json
import logging
import os
from aiohttp import web
import aiohttp_jinja2
import jinja2
import aiohttp
from kubernetes_asyncio import client, config

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenTelemetry Configuration
otlp_endpoint = os.environ.get("OTLP_ENDPOINT", "localhost:4318")
otlp_tls = os.environ.get("OTLP_TLS", "false").lower() in ("true", "1", "yes")

if not otlp_endpoint.startswith("http"):
    scheme = "https" if otlp_tls else "http"
    otlp_url = f"{scheme}://{otlp_endpoint}/v1/metrics"
else:
    otlp_url = otlp_endpoint

resource = Resource.create({"service.name": "monitor-ui", "job": "curl"})
exporter = OTLPMetricExporter(endpoint=otlp_url)
reader = PeriodicExportingMetricReader(exporter, export_interval_millis=1000)
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)

meter = metrics.get_meter("monitor-ui")
frontend_counter = meter.create_counter(
    "frontend_requests_total",
    description="Total number of frontend requests",
)
backend_counter = meter.create_counter(
    "backend_requests_total",
    description="Total number of backend requests",
)

# Global state
current_uri = os.environ.get("URI", "https://10.89.0.200")
is_running = True
discovered_uris = []
stats = {
    "frontend": {},  # pod_name: {"count": 0, "latest_delay": 0.0}
    "backend": {},   # pod_name: {"count": 0, "latest_delay": 0.0}
}
websockets = set()
SCRIPT_START_TIME = time.time()


async def get_k8s_client():
    try:
        config.load_incluster_config()
    except config.ConfigException:
        try:
            await config.load_kube_config()
        except config.ConfigException:
            # Fallback for explicit token file (e.g., OpenShift token injected via file)
            configuration = client.Configuration()
            configuration.host = os.environ.get("KUBERNETES_HOST", "https://kubernetes.default.svc")
            token_file = os.environ.get("KUBERNETES_TOKEN_FILE", "/var/run/secrets/kubernetes.io/serviceaccount/token")
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                configuration.api_key['authorization'] = token
                configuration.api_key_prefix['authorization'] = 'Bearer'
                
                ca_file = os.environ.get("KUBERNETES_CA_FILE", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
                if os.path.exists(ca_file):
                    configuration.ssl_ca_cert = ca_file
                else:
                    configuration.verify_ssl = False
                client.Configuration.set_default(configuration)
            else:
                raise Exception("Could not configure Kubernetes client: no in-cluster config, no kubeconfig, and no token file found.")
    return client.ApiClient()

async def discover_uris_task(app):
    global discovered_uris
    while True:
        try:
            async with await get_k8s_client() as api_client:
                core_v1 = client.CoreV1Api(api_client)
                services = await core_v1.list_namespaced_service("gateways")
                uris = []
                for svc in services.items:
                    if svc.spec.type == "LoadBalancer":
                        # Check ingress IPs
                        if svc.status.load_balancer.ingress:
                            for ing in svc.status.load_balancer.ingress:
                                ip = ing.ip or ing.hostname
                                if ip:
                                    uris.append(f"https://{ip}")
                        # Also check external IPs if they are set directly
                        if hasattr(svc.spec, 'external_ips') and svc.spec.external_ips:
                            for ip in svc.spec.external_ips:
                                uris.append(f"https://{ip}")
                
                # Sort to ensure consistent order and remove duplicates
                uris = sorted(list(set(uris)))
                
                if uris != discovered_uris:
                    discovered_uris = uris
                    # Broadcast new URIs to connected clients
                    msg = json.dumps({"type": "uris", "uris": discovered_uris})
                    for ws in list(websockets):
                        try:
                            await ws.send_str(msg)
                        except Exception:
                            websockets.discard(ws)
        except Exception as e:
            logger.error(f"Error discovering URIs from gateways namespace: {e}")
        
        await asyncio.sleep(30)

async def frontend_monitor_task(app):
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            if not is_running:
                await asyncio.sleep(0.5)
                continue
                
            start_time = time.time()
            try:
                async with session.get(
                    current_uri,
                    headers={"Host": "http.apps.example.com"},
                    server_hostname="http.apps.example.com",
                    timeout=5,
                ) as resp:
                    data = await resp.json()
                    pod_full = data.get("env", {}).get("HOSTNAME")
                    # Strip the random suffix to group by deployment (e.g., http-v1-869fdbfc47-vg95z -> http-v1)
                    pod = "-".join(pod_full.split("-")[:-2]) if pod_full and pod_full.count("-") >= 2 else pod_full
                    delay = time.time() - start_time

                    if pod:
                        if pod not in stats["frontend"]:
                            stats["frontend"][pod] = {"count": 0, "latest_delay": 0.0}
                        stats["frontend"][pod]["count"] += 1
                        stats["frontend"][pod]["latest_delay"] = delay

                        # Broadcast to websockets
                        msg = json.dumps(
                            {
                                "type": "update",
                                "target": "frontend",
                                "pod": pod,
                                "pod_full": pod_full,
                                "count": stats["frontend"][pod]["count"],
                                "delay": delay,
                            }
                        )
                        for ws in list(websockets):
                            try:
                                await ws.send_str(msg)
                            except Exception:
                                websockets.discard(ws)

                        # Send OTLP metrics
                        try:
                            frontend_counter.add(1, {"job": "curl_frontend", "pod": pod, "pod_full": pod_full})
                        except Exception as e:
                            logger.error(f"OTLP error: {e}")
            except Exception as e:
                logger.error(f"Frontend monitor error: {e}")

            await asyncio.sleep(0.5)


async def backend_monitor_task(app):
    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        while True:
            if not is_running:
                await asyncio.sleep(0.5)
                continue
                
            start_time = time.time()
            try:
                uri = current_uri.rstrip("/") + "/proxy/"
                async with session.post(
                    uri,
                    headers={"Host": "http.apps.example.com", "zone": "zone1", "Content-Type": "application/x-www-form-urlencoded"},
                    server_hostname="http.apps.example.com",
                    data="proxy=" + os.environ.get("BACKEND", "http://backend.backends.svc:8080"),
                    timeout=5,
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"Backend monitor proxy returned status {resp.status}")
                        await asyncio.sleep(0.5)
                        continue
                        
                    data = await resp.json()
                    
                    # The proxy returns {"proxy": "...", "body": "..."}
                    # If proxy is "http://localhost:8080/no-proxy", it means our proxy param wasn't read correctly
                    if data.get("proxy") == "http://localhost:8080/no-proxy":
                        logger.error("Proxy failed to read proxy parameter, returning no-proxy")
                    
                    body_str = data.get("body")
                    if body_str:
                        try:
                            if isinstance(body_str, str):
                                body_data = json.loads(body_str)
                            else:
                                body_data = body_str
                            
                            pod_full = body_data.get("env", {}).get("HOSTNAME")
                            # Strip the random suffix to group by deployment (e.g., http-v1-869fdbfc47-vg95z -> http-v1)
                            pod = "-".join(pod_full.split("-")[:-2]) if pod_full and pod_full.count("-") >= 2 else pod_full
                        except json.JSONDecodeError:
                            logger.error("Failed to parse backend body as JSON")
                            pod = None
                            
                        delay = time.time() - start_time

                        if pod:
                            if pod not in stats["backend"]:
                                stats["backend"][pod] = {"count": 0, "latest_delay": 0.0}
                            stats["backend"][pod]["count"] += 1
                            stats["backend"][pod]["latest_delay"] = delay

                            # Broadcast to websockets
                            msg = json.dumps(
                                {
                                    "type": "update",
                                    "target": "backend",
                                    "pod": pod,
                                    "pod_full": pod_full,
                                    "count": stats["backend"][pod]["count"],
                                    "delay": delay,
                                }
                            )
                            for ws in list(websockets):
                                try:
                                    await ws.send_str(msg)
                                except Exception:
                                    websockets.discard(ws)

                            # Send OTLP metrics
                            try:
                                backend_counter.add(1, {"job": "curl_backend", "pod": pod, "pod_full": pod_full})
                            except Exception as e:
                                logger.error(f"OTLP error: {e}")
            except Exception as e:
                logger.error(f"Backend monitor error: {e}")

            await asyncio.sleep(0.5)


async def deployment_monitor_task(app):
    while True:
        try:
            async with await get_k8s_client() as api_client:
                apps_v1 = client.AppsV1Api(api_client)
                deployments_to_watch = ["http-v1", "http-v2", "http-v3", "backend-v1", "backend-v2", "backend-v3"]
                
                deployment_status = {}
                for dep in deployments_to_watch:
                    ns = "frontends" if dep.startswith("http-") else "backends"
                    try:
                        resp = await apps_v1.read_namespaced_deployment(name=dep, namespace=ns)
                        deployment_status[dep] = resp.spec.replicas
                    except Exception as e:
                        # Deployment might not exist or no permission
                        pass
                
                if deployment_status:
                    msg = json.dumps({"type": "deployments_status", "statuses": deployment_status})
                    for ws in list(websockets):
                        try:
                            await ws.send_str(msg)
                        except Exception:
                            websockets.discard(ws)
        except Exception as e:
            logger.error(f"Error in deployment monitor: {e}")
        
        await asyncio.sleep(2.0)

async def start_background_tasks(app):
    app["frontend_monitor"] = asyncio.create_task(frontend_monitor_task(app))
    app["backend_monitor"] = asyncio.create_task(backend_monitor_task(app))
    app["discover_uris"] = asyncio.create_task(discover_uris_task(app))
    app["deployment_monitor"] = asyncio.create_task(deployment_monitor_task(app))

async def cleanup_background_tasks(app):
    app["frontend_monitor"].cancel()
    app["backend_monitor"].cancel()
    app["discover_uris"].cancel()
    app["deployment_monitor"].cancel()
    await app["frontend_monitor"]
    await app["backend_monitor"]
    await app["discover_uris"]
    await app["deployment_monitor"]


@aiohttp_jinja2.template("index.html")
async def index(request):
    return {}


async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    websockets.add(ws)

    try:
        await ws.send_str(json.dumps({
            "type": "init", 
            "stats": stats, 
            "uri": current_uri, 
            "is_running": is_running,
            "uris": discovered_uris
        }))
        async for msg in ws:
            pass
    finally:
        websockets.discard(ws)
    return ws


async def update_uri(request):
    global current_uri
    try:
        data = await request.json()
        new_uri = data.get("uri")
        if new_uri:
            current_uri = new_uri
            return web.json_response({"status": "success", "message": f"URI updated to {current_uri}"})
        return web.json_response({"status": "error", "message": "No URI provided"}, status=400)
    except Exception as e:
        logger.error(f"Error updating URI: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def scale_deployments(request):
    try:
        data = await request.json()
        deployments_to_scale = data.get("deployments", [])
        replicas = data.get("replicas", 0)
        
        if not deployments_to_scale:
            return web.json_response({"status": "error", "message": "No deployments selected"}, status=400)

        try:
            config.load_incluster_config()
        except config.ConfigException:
            try:
                await config.load_kube_config()
            except config.ConfigException:
                # Fallback for explicit token file (e.g., OpenShift token injected via file)
                configuration = client.Configuration()
                configuration.host = os.environ.get("KUBERNETES_HOST", "https://kubernetes.default.svc")
                token_file = os.environ.get("KUBERNETES_TOKEN_FILE", "/var/run/secrets/kubernetes.io/serviceaccount/token")
                if os.path.exists(token_file):
                    with open(token_file, 'r') as f:
                        token = f.read().strip()
                    configuration.api_key['authorization'] = token
                    configuration.api_key_prefix['authorization'] = 'Bearer'
                    
                    ca_file = os.environ.get("KUBERNETES_CA_FILE", "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
                    if os.path.exists(ca_file):
                        configuration.ssl_ca_cert = ca_file
                    else:
                        configuration.verify_ssl = False
                    client.Configuration.set_default(configuration)
                else:
                    raise Exception("Could not configure Kubernetes client: no in-cluster config, no kubeconfig, and no token file found.")

        async with client.ApiClient() as api_client:
            apps_v1 = client.AppsV1Api(api_client)
            namespace = "lbmonitor"

            try:
                with open(
                    "/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r"
                ) as f:
                    namespace = f.read().strip()
            except FileNotFoundError:
                namespace = os.environ.get("NAMESPACE", "default")

            for dep in deployments_to_scale:
                try:
                    body = {"spec": {"replicas": replicas}}
                    ns = "frontends" if dep.startswith("http-") else "backends"
                    await apps_v1.patch_namespaced_deployment_scale(
                        name=dep, namespace=ns, body=body
                    )
                    logger.info(f"Scaled deployment {dep} in {ns} to {replicas}")
                except Exception as e:
                    logger.error(f"Failed to scale {dep}: {e}")

        action = "Scale up" if replicas > 0 else "Shutdown"
        return web.json_response(
            {"status": "success", "message": f"{action} initiated for {', '.join(deployments_to_scale)}"}
        )
    except Exception as e:
        logger.error(f"Error in scale: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def reset_counters(request):
    try:
        for target in ["frontend", "backend"]:
            for pod in stats[target]:
                stats[target][pod]["count"] = 0
                
        msg = json.dumps({"type": "reset"})
        for ws in list(websockets):
            try:
                await ws.send_str(msg)
            except Exception:
                websockets.discard(ws)
                
        return web.json_response({"status": "success", "message": "Counters reset"})
    except Exception as e:
        logger.error(f"Error resetting counters: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def toggle_running(request):
    global is_running
    try:
        is_running = not is_running
        msg = json.dumps({"type": "toggle", "is_running": is_running})
        for ws in list(websockets):
            try:
                await ws.send_str(msg)
            except Exception:
                websockets.discard(ws)
        return web.json_response({"status": "success", "is_running": is_running})
    except Exception as e:
        logger.error(f"Error toggling state: {e}")
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def app_factory():
    app = web.Application()
    # Setup jinja2 template resolution
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(template_dir))

    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_post("/api/scale", scale_deployments)
    app.router.add_post("/api/uri", update_uri)
    app.router.add_post("/api/reset", reset_counters)
    app.router.add_post("/api/toggle", toggle_running)

    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    return app


if __name__ == "__main__":
    print(f"Running on {os.environ.get('API')}")
    web.run_app(app_factory(), port=int(os.environ.get("PORT", 8080)))
