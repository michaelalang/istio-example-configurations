# Soft Multi-Tenancy with a Shared Gateway

This use case demonstrates a soft multi-tenancy setup where multiple tenants share the same Istio gateway but have their own separate namespaces and services.

## Summary

This scenario provides a simple example of how to achieve multi-tenancy in Istio without requiring a separate gateway for each tenant. This can be a cost-effective and efficient way to manage multiple tenants in a single service mesh.

The key components of this configuration are:

*   **Shared Gateway:** A single Istio gateway is deployed and shared by all tenants. The gateway is configured to handle traffic for a common host (e.g., `http.apps.example.com`).
*   **Tenant Namespaces:** Each tenant is assigned its own namespace (e.g., `tenanta`, `tenantb`). This provides a basic level of isolation for their resources.
*   **Tenant-Specific Routing:** Each tenant has its own `VirtualService` in its own namespace. This `VirtualService` is configured to route traffic for the shared host to the tenant's specific service within their own namespace.

This approach is considered "soft" multi-tenancy because the tenants are not completely isolated from each other. For example, they share the same Istio control plane and gateway. However, it provides a good balance between isolation and resource utilization for many use cases.

## Deployment

* execute following command to deploy `tenant-a` and `tenant-b` namespace resources

```
oc create -k .
```

## Verify tenancy 

* execute following command to verify the visible xDS resources in the tenant-a namespace 

```
istioctl -n tenant-a pc all deploy/http
```

* verify that only `tenant-a` and `istio-system` namespace based resources are visible

* execute following command to verify the visible xDS resources in the tenant-b namespace 

```
istioctl -n tenant-b pc all deploy/http
```

* verify that only `tenant-b` and `istio-system` namespace based resources are visible

## Test Cases

To test this configuration, you can perform the following checks:

1.  **Access Tenant A's service:**
    *   Send a request to the shared host (`http.apps.example.com`).
    *   You will need to ensure that your request is routed to the gateway in Tenant A's namespace. How you do this will depend on your specific environment. For example, you might use a different ingress IP for each tenant's gateway, or you might use a higher-level load balancer to route traffic based on some criteria.
    *   **Expected result:** You should receive a response from the `http` service in the `tenanta` namespace.

2.  **Access Tenant B's service:**
    *   Send a request to the shared host (`http.apps.example.com`), ensuring that the request is routed to the gateway in Tenant B's namespace.
    *   **Expected result:** You should receive a response from the `http` service in the `tenantb` namespace.

3.  **Verify isolation:**
    *   From a pod in Tenant A's namespace, try to access a service in Tenant B's namespace directly.
    *   **Expected result:** The request should be denied, unless you have explicitly configured an `AuthorizationPolicy` to allow it.
