# Egress Traffic through an External Proxy

This use case demonstrates how to route egress traffic from the service mesh through an external proxy, in this case, a Squid proxy. It presents two different approaches: using an egress gateway and a transparent proxy.

**Disclaimer:** The transparent Proxy scenarios use `EnvoyFilter`, which is not supported by Red Hat for Service Mesh configurations. Using `EnvoyFilter` can have unintended consequences and should be done with extreme caution.

## Summary

This scenario addresses the common requirement of routing all outbound traffic through a central proxy for security, monitoring, or policy enforcement purposes.

### Egress Gateway Approach

In this approach, we use an Istio egress gateway to explicitly control the flow of traffic leaving the mesh.

*   **Egress Gateway:** An egress gateway is deployed and configured to handle traffic for specific hosts (e.g., `*.google.com`).
*   **VirtualService:** A `VirtualService` is created to match traffic at the egress gateway and route it to the external Squid proxy.
*   **ServiceEntry:** `ServiceEntry` resources are used to make the external Squid proxy known to the Istio service mesh.

This approach provides a clear and explicit way to manage egress traffic, but it requires more configuration than the transparent proxy approach.

#### Deployment

* ensure to update the followin resource to reflect the IP address of your Proxy
    * serviceentry.yml
    * destinationrule.yml
* execute the following command to deploy the sample client

```
oc create -k .
```

* Extract the Proxy CA certificate and the Cluster Trust bundle to update the `proxy-trust-bundle.yml` configMap.
```
mkdir certs && cd certs
oc -n proxytest extract secret/gateway-secret 
chmod 0644 *
chcon -t container_file_t -R ../certs
cd -
```
* ensure to restart the client pod to pickup the ceritficates accordingly

```
oc -n proxytest rollout restart deploy/http
```

* execute the following command to create your Squid Proxy image

```
podman build -f Dockerfile -t squid:latest
```

* execute the following command to start the Squid Proxy accordingly

```
./run-proxy.sh

# alternative run the pod manually
# podman run -d --rm --replace --name squid-proxy    -p 8080:8080 -p 8443:8443   -v ./certs:/certs:ro,z  squid:latest
```

* execute a curl command in the deployed client

```
oc -n proxytest exec -ti deploy/http -- /bin/bash
# either export or use the command line parameter to use the proxy
curl -x http://squid-proxy:8080 https://www.google.com -I
curl -x https://squid-proxy:8443 https://www.google.com -I
```

### Transparent Proxy Approach

In this approach, we use a `VirtualService` to transparently intercept and redirect egress traffic to the Squid proxy, without the need for an egress gateway.

*   **VirtualService:** A `VirtualService` is configured to match traffic destined for specific external hosts (e.g., `*.google.com`) and route it directly to the Squid proxy.
*   **ServiceEntry:** As in the egress gateway approach, `ServiceEntry` resources are used to register the Squid proxy with the mesh.

This approach is simpler to configure than the egress gateway approach, but it may be less explicit and harder to debug.


#### Deployment

* ensure to update the followin resource to reflect the IP address of your Proxy
    * transparent/se-squid.yml
* execute the following command to update the configurations

```
oc apply -k transparent
```
* execute a curl command in the deployed client

```
oc -n proxytest exec -ti deploy/http -- /bin/bash
curl https://www.google.com -I
```

* check your proxy logs to verify the connection was handled accordingly

```
podman logs --tail 1 squid-proxy 
1774199180.483   2594 <node.ip> TCP_TUNNEL/200 4674 CONNECT www.google.com:443 - HIER_DIRECT/142.251.153.119 -
```

### Transparent Proxy Approach through an EGress gateway

In this approach, we use a `VirtualService` to transparently intercept and redirect egress traffic to the Squid proxy, without the need for an egress gateway.

*   **VirtualService:** A `VirtualService` is configured to match traffic destined for specific external hosts (e.g., `*.google.com`) and route it directly to the Squid proxy.
*   **ServiceEntry:** As in the egress gateway approach, `ServiceEntry` resources are used to register the Squid proxy with the mesh.


* ensure to update the followin resource to reflect the IP address of your Proxy
    * egress/se-squid.yml
* execute the following command to update the configurations

```
oc apply -k egress
```

* remove the following virtualservice configuration 

```
oc -n proxytest delete virtualservice.networking.istio.io/enforce-squid-proxy
```

* execute a curl command in the deployed client

```
oc -n proxytest exec -ti deploy/http -- /bin/bash
curl https://www.google.com -I
```

* check the egressgateway logs to verify the connection was handled accordingly

```
oc -n proxytest logs deployments/egressgateway | grep "authority', 'www.google.com"
```

* check your proxy logs to verify the connection was handled accordingly

```
podman logs --tail 1 squid-proxy 
1774199180.483   2594 <node.ip> TCP_TUNNEL/200 4674 CONNECT www.google.com:443 - HIER_DIRECT/142.251.153.119 -
```

* move the Egress Pod to a different node to ensure `<node.ip>` changes in the Squid Proxy logs accordingly

```
oc -n proxytest patch deployment/egressgateway --type=merge \
  -p '{"spec":{"template":{"spec":{"nodeSelector":{"kubernetes.io/hostname":"<node.name"}}}}}'
```

* execute a curl command in the deployed client

```
oc -n proxytest exec -ti deploy/http -- /bin/bash
curl https://www.google.com -I
```

* check your proxy logs to verify the ip has changed accordingly

```
$ podman logs squid-proxy --tail 1
1774199983.041    417 192.168.192.54 TCP_TUNNEL/200 4674 CONNECT www.google.com:443 - HIER_DIRECT/142.251.151.119 -
```

## Test Cases

To test this configuration, you can perform the following checks for both approaches:

1.  **Access an external service from within the mesh:**
    *   From a pod within the mesh, send a request to an external service that should be routed through the proxy (e.g., `curl http://www.google.com`).
    *   **Expected result:** The request should be successful, and the traffic should be routed through the Squid proxy.

2.  **Verify traffic flows through the proxy:**
    *   Check the logs of the Squid proxy to confirm that it is receiving and forwarding traffic from the service mesh.
    *   **Expected result:** You should see log entries in the Squid proxy's access log corresponding to the requests you made from within the mesh.

3.  **Access an external service that is not configured to go through the proxy:**
    *   If you have configured the proxy to only handle traffic for specific hosts, try accessing a different external service.
    *   **Expected result:** The request should either fail or be routed directly to the external service, depending on your mesh's outbound traffic policy.
