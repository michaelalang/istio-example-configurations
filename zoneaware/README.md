# Zone Aware Routing

This use case demonstrates three different ways to get best possible routing decision when considering multi-cluster and or firesection zones.

## Labeling your Cluster nodes for locality based loadbalancing

**NOTE kuberentes topology labels will have an impact of your workloads when being deployed and shall only be set in alignment with the infrastructure Team and any external infrastructure provider like VSphere to comply with topology configurations through all management tools.**

Following labels can be applied to make your workload and your ServiceMesh loadbalancing locality aware:

* `topology.kubernetes.io/region`
* `topology.kubernetes.io/zone`
* `topology.istio.io/subzone`

Alternatively, you can manually inject the `istio-locality` label directly into your pod templates (e.g. `istio-locality: region.zone.subzone`). This is the approach used in this demo to simulate a multi-region environment on a single cluster without modifying the node labels.

## Gateway alignment

Envoys [documentation](https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/locality_weight.html) outlines, locality based loadbalancing will try to deiliver within it's own zone until there are no healthy endpoints available. In scenarios were your Gateway forwards the traffic to region/zone/subzone2 instead of region/zone/subzone1 means that your Gateway is not part of the region/zone/subzone1 eventhough all endpoints are up and healthy.

Adjust your Gateway injection template accordingly to your needs and preferred region/zone/subzone setup.


## Cluster Setup (KinD & MetalLB)

**NOTE** since we need to access the IngressIP's rootless podman isn't working and you need sudo access to deploy the demo cluster

This demo is designed to run locally using [KinD (Kubernetes in Docker)](https://kind.sigs.k8s.io/). To support `LoadBalancer` services locally, we use MetalLB.

1. **Create the KinD Cluster:**
   Use the provided `setup-kind.sh` script to create the cluster with the custom `kind-config.yaml`:
   ```bash
   ./setup-kind.sh
   ```

2. **Configure MetalLB:**
   The `setup-kind.sh` script automatically installs MetalLB. It also applies the `metallb-config.yaml` to provide a pool of IP addresses for your `LoadBalancer` services. Ensure the IP range in `metallb-config.yaml` matches your Docker network subnet.

## Deployment

The deployment simulates multi-cluster and multi-region by manually `overwriting` the topology on the deployment level using the `istio-locality` label (e.g., `istio-locality: east.zone1.sub1`). **NOTE** this is unsupported by Red Hat and only used to serve the demonstration purpose with a single cluster.

### Certificate and Domains

The demo uses Cert-Manager as certificate provider (cert.yml). Ensure to provide a valid TLS certificate for the domain(s) you want to serve on the application accordingly.
The demo uses `apps.example.com` as base domain to service application traffic. Ensure to adjust the domain according to you infrastructure.

* update `cert.yml` accordingly to create or provide a valid ingress TLS certificate
* update following files to reflect the proper base domain and fqdn for your ingress
    * cert.yml
    * gateway-v1-cfg.yml
    * gateway-v2-cfg.yml
    * vs.yml
* update the namespace `istio.io/rev` label accordingly to match your ServiceMesh `discoverySelector` 
* execute following command to deploy the application stack:
    * 3 Namespaces (`frontends`, `backends`, `gateways`) with corresponding ServiceAccounts
    * Cert-Manager Issuers and Certificates for TLS
    * 2 Istio Ingress Gateways (`gateway-v1`, `gateway-v2`) with `LoadBalancer` services
    * 3 Frontend HTTPBin deployments (`http-v1`, `http-v2`, `http-v3`) serving different regions
    * 3 Backend HTTPBin deployments (`backend-v1`, `backend-v2`, `backend-v3`) serving different regions
    * Istio VirtualServices and DestinationRules for routing
    * OpenTelemetry Collector and VictoriaMetrics for observability

```bash 
oc create -k application
oc create -k ui/k8s/
oc -n frontends wait deploy/http-v1 deploy/http-v2 deploy/http-v3 --for=condition=Available --timeout=180s
oc -n backends wait deploy/backend-v1 deploy/backend-v2 deploy/backend-v3 --for=condition=Available --timeout=180s
oc -n lbmonitor wait deploy/lbmonitor --for=condition=Available --timeout=180s
```

* after the deployments have been started ensure all resources are alligned (since we don't use a GitOps controller)

```
for x in gateways frontends backends lbmonitor ; do oc -n ${x} delete pod --all --wait=false ; done
```


#### Routing Legend:
* Solid, Thick Arrows (==>): Represent the primary "stick" priority. Traffic is pinned to endpoints matching the originating gateway's specific Region.
* Dotted Arrows (-.->): Represent the failover progression triggered only when the higher-priority endpoints become unavailable.
* Topology Hierarchy: The nested boxes visualize the locality structure (east -> west -> backup) that Istio uses to calculate endpoint proximity for these failover rules.

```mermaid
flowchart TD
    %% External Ingress Traffic
    InEast([Ingress Traffic]) --> GW1
    InWest([Ingress Traffic]) --> GW2

    %% Topology Boundaries
    subgraph Region_East [Region: east]
        direction TB
        subgraph Zone_East1 [Zone: zone1]
            subgraph Sub_East1 [Subzone: sub1]
                GW1[gateway-v1]
                SVC1(http-v1 endpoints)
            end
        end
    end
    
    subgraph Region_West [Region: west]
        direction TB
        subgraph Zone_West1 [Zone: zone1]
            subgraph Sub_West1 [Subzone: sub1]
                GW2[gateway-v2]
                SVC2(http-v2 endpoints)
            end
        end
    end
    
    subgraph Region_Backup [Region: backup]
        direction TB
        subgraph Zone_Backup1 [Zone: zone1]
            subgraph Sub_Backup1 [Subzone: sub1]
                SVC3(http-v3 endpoints)
            end
        end
    end

    %% Gateway 1 Routing Logic (East)
    GW1 ==>|1. Stick| SVC1
    GW1 -.->|2. Failover| SVC2
    GW1 -.->|3. Failover| SVC3

    %% Gateway 2 Routing Logic (West)
    GW2 ==>|1. Stick| SVC2
    GW2 -.->|2. Failover| SVC1
    GW2 -.->|3. Failover| SVC3

    %% Styling and coloring for clarity
    classDef gateway fill:#e1f5fe,stroke:#0288d1,stroke-width:2px,color:#000
    classDef primary fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#000
    classDef backup fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#000
    classDef ingress fill:#f5f5f5,stroke:#9e9e9e,stroke-width:1px,color:#000
    
    class GW1,GW2 gateway
    class SVC1,SVC2 primary
    class SVC3 backup
    class InEast,InWest ingress
```

## Verification and configuration for the setup

* execute following to start the UI
```
oc -n lbmonitor wait deploy/lbmonitor --for=condition=Available --timeout=180s
oc -n lbmonitor get service lbmonitor -o jsonpath='{.status.loadBalancer.ingress[0].ip}' ; echo
```

* Point your Browser against the IP on port `8080`

![SimpleUI localitybased LoadBalancing](pictures/lbui001.png)


* Ensure, locality loadbalancing is enabled by executing following command

```
oc -n frontends patch destinationRule/http --type=merge -p '{"spec":{"trafficPolicy":{"loadBalancer":{"localityLbSetting":{"enabled":true}}}}}' 
```

* The UI will show that only `http-v1` receives requests now.

![localitybased LoadBalancing](pictures/lbui002.png)

* hit the second Ingress Gateway to ensure, stickiness to the locality applies there too

![localitybased LoadBalancing](pictures/lbui003.png)


### verify locality based failover to region west

* simulate an outage of the primary region (http-v1,backend-v1) by shutting down the service.

![localitybased LoadBalancing](pictures/lbui004.png)

* the Gateway automatically switched to the second zone

### verify locality based failover to backup cluster

* simulate an outage of the secondary region (http-v2,backend-v2) by shutting down the service.

![localitybased LoadBalancing](pictures/lbui005.png)

* check if switching the Ingress gateway uses http-v3 and backend-v3 as well.

* scale up all instances again 

![localitybased LoadBalancing](pictures/lbui006.png)

## Zoneaware latency 

* simulate an outage of the backend in the primary region (backend-v1) by shutting down the service.

![localitybased LoadBalancing](pictures/lbui007.png)

* backend failovers transparently but latency is increased (simulated to show-case cross-site costs)

* simulate an outage of the backend in the secondary region (backend-v2) by shutting down the service.

![localitybased LoadBalancing](pictures/lbui008.png)

* backend failover transparently but latency increased even more (simulated)

* simulate an outage of the frontend in the primary region (http-v1).

![localitybased LoadBalancing](pictures/lbui009.png)

* with ingress misalignment we increased the frontend latency and in addition the backend latency.

* hit the second Ingress Gateway to algin ingress and frontend at least.

![localitybased LoadBalancing](pictures/lbui010.png)

* scale up all instances again

## Cleanup

* remove all configurations by executing following command

```
sudo KIND_EXPERIMENTAL_PROVIDER=podman /home/milang/bin/kind delete clusters openshiftanwendertreffen
```

* remove all system configurations by executing following command

```
sudo rm -f /etc/sysctl.d/99-kind-podman.conf
sudo sysctl --system
```

## Conclusion: Zone Aware Routing Showcase

In this demonstration, we showcased how to configure and validate locality-based load balancing in a ServiceMesh to ensure the most efficient routing decisions across multi-cluster and multi-zone environments.

Here is a summary of what was accomplished:

* **Topology Simulation**: We simulated a multi-region and multi-cluster environment by applying the `istio-locality` label directly at the deployment level, bypassing the need to modify cluster node labels.
* **Baseline Routing Observation**: We observed the default LEAST_REQUEST Envoy behavior, which shuffles traffic across all available endpoints indiscriminately, including higher-latency endpoints located in completely different clusters.
* **Enabling Locality Stickiness**: By patching the `DestinationRule` with `localityLbSetting` enabled, we demonstrated how to pin ingress traffic to the closest local endpoints, ensuring a gateway prefers its own subzone first.
* **Intra-Region Failover**: We simulated an outage of the primary region by scaling the `http-v1` deployment to zero replicas. We then verified that the gateway automatically and successfully failed over to the next available region (`http-v2` in `west`).
* **Cross-Cluster Failover**: We simulated a broader regional failure by also scaling the secondary region (`http-v2`) to zero. We successfully validated that traffic seamlessly fell back to the backup cluster (`http-v3` in `backup`).
* **Backend Locality**: We proved that the exact same locality-based routing rules apply transparently to internal service-to-service communication (Frontend -> Backend).
* **Real-time Visualization**: We provided an interactive dashboard to visually demonstrate the failover mechanisms, request distributions, and the resulting latency impacts in real-time.

Ultimately, this exercise proved how to build a highly resilient, latency-optimized routing topology using Istio's native locality awareness to handle cascading failures gracefully.
