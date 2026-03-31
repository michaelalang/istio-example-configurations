# GRPC mesh timeout configuration 

## build custom GRPC service 

* the client enforces ALPN/SNI inside the code so that one can execute a call against an IP address
* ensure to change the string `grpc.apps.example.com` if you cannot expose this FQDN in your infrastructure.
* execute following command to build the simple grpc service 
```
cd application
podman build -f Dockerfile -t <your-registry>/grpc:v1.0.0
```

* push the image to your registry 
* adjust the kustomization file in the directory argocd 

```
images:
- name: localhost/grpc
  newName: quay.io/your-repo/grpc
```

## deploy the application 

**NOTE** the repository ships only a Cert-Manager template as well as an ExternalSecret for the sensitive data required

* Adjust the `argocd/cert.yml` file or deploy your own Certificate accordingly
* Adjust the `argocd/secret.yml` file to provide pull-secret credentials for your image
* Adjust the following hostname CRs to match your infrastructure
    * argocd/gateway.yml
    * argocd/virtualservice.yml
    * argocd/route.yml
* execute following command to deploy the resources 

```
oc create -k argocd
```

## executing the client to call the server 

* execute the following command to enter the server pod which has the client script

```
oc -n meshgrpc exec -ti deploy/grpcserver-stable -- /bin/bash
```

* inside the container depending on your expose strategy for the service execute 

```
# through Route or LoadBalancer SSL
SLEEP_S=20 SLEEP_C=18 GRPC_TARGET=<ip>:<port> python ssl_client.py 

# plain-text through service 
SLEEP_S=20 SLEEP_C=18 GRPC_TARGET=<ip>:<port> python client.py 
```

### troubleshooting

No matter which access you have choosen you should see an error like
```
INFO:root:Calling server: Asking to sleep for 20s, Client timeout is 18s.
ERROR:root:Istio Proxy Timeout (HTTP 504 Gateway Timeout): upstream request timeout
```

If you have choosen the LoadBalancer SSL path

* adjust the route to not have any timeout accordingly 

```
oc -n meshgrpc annotate route grpc haproxy.router.openshift.io/timeout="0s"
```

* continue on the service path resolution for the problem too

If you have choosen the service path 

* adjust the virtualservice to not have timeout configured on the matche

```
oc patch virtualservice grpcserver \
  --type='json' \
  -p='[{"op": "remove", "path": "/spec/http/0/timeout"}]'
```

* retry the client communication accordingly 

```
# through Route or LoadBalancer SSL
SLEEP_S=20 SLEEP_C=18 GRPC_TARGET=<ip>:<port> python ssl_client.py

# plain-text through service
SLEEP_S=20 SLEEP_C=18 GRPC_TARGET=<ip>:<port> python client.py
```

