# Kubernetes Gateway API vs. Istio Gateway

This use case provides a side-by-side comparison of the Kubernetes Gateway API and the traditional Istio Gateway for exposing a service to external traffic.

## Summary

This example demonstrates how to achieve the same result—exposing an HTTP service—using two different sets of APIs. This is useful for understanding the differences between the two approaches and for migrating from the Istio Gateway to the more standardized Kubernetes Gateway API.

The deployments require a `LoadBalancer` service to show-case the various deployments being accessible at the same time.

### Kubernetes Gateway API (`gwapi` directory)

The Kubernetes Gateway API is a new standard for configuring gateways and routing in Kubernetes. It's designed to be more expressive, extensible, and role-oriented than the Ingress API.

*   **`Gateway`:** This resource defines the gateway itself, including the ports and protocols it listens on. The `gatewayClassName` field specifies the controller that should manage this gateway.
*   **`HTTPRoute`:** This resource defines the routing rules for HTTP traffic. It's used to route requests to different services based on hostnames, paths, and other criteria.

### Istio Gateway (`istio` directory)

The Istio Gateway is the traditional way of configuring gateways in Istio. It's a powerful and flexible API, but it's specific to Istio.

*   **`Gateway`:** This Istio resource defines the gateway, similar to the Kubernetes Gateway API's `Gateway` resource.
*   **`VirtualService`:** This Istio resource defines the routing rules for traffic, similar to the Kubernetes Gateway API's `HTTPRoute` resource.

### OpenShift Route to Istio Gateway

The OpenShift Route in `passthrough` is the traditional way of configuring gateways in OpenShift. 

*   **`Route`:** This route exposes the service on the OpenShift Ingress (HAProxy) service.
*   **`Gateway`:** This Istio resource defines the gateway, similar to the Kubernetes Gateway API's `Gateway` resource.
*   **`VirtualService`:** This Istio resource defines the routing rules for traffic, similar to the Kubernetes Gateway API's `HTTPRoute` resource.

## Test Cases

To test this configuration, you can perform the following checks for both the `gwapi` and `istio` configurations:

1.  **Access the service from outside the cluster:**
    *   Send a request to the host that is configured in the `HTTPRoute` (for `gwapi`) or `VirtualService` (for `istio`).
    *   **Expected result:** You should receive a response from the backend service.

2.  **Verify the routing:**
    *   If you have configured multiple routes, you can test each one to ensure that it's routing traffic to the correct service.
    *   **Expected result:** The traffic should be routed according to the rules you have defined.