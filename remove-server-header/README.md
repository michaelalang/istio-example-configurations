# Remove Server Headers from HTTP Response

This use case demonstrates how to remove specific headers from the HTTP response using an `EnvoyFilter`.

**Disclaimer:** This scenario uses `EnvoyFilter`, which is not supported by Red Hat for Service Mesh configurations. Using `EnvoyFilter` can have unintended consequences and should be done with extreme caution.

## Summary

For security and information hiding purposes, it's often desirable to remove certain headers from the HTTP response that might reveal information about the underlying server and proxy infrastructure. This example uses `EnvoyFilter` to remove the following headers:

*   `server`: This header often contains information about the web server software being used (e.g., `nginx`, `Apache`).
*   `x-envoy-upstream-service-time`: This header is added by Envoy and indicates the time it took for the upstream service to respond.
*   `x-powered-by`: This header is often added by application frameworks and can reveal the technology used to build the application (e.g., `Express`, `PHP`).

This example provides two `EnvoyFilter` resources:

*   **`gateway-response-remove-headers`:** This filter applies to the Istio gateway and removes the specified headers from the response before it's sent to the client.
*   **`response-headers-filter`:** This filter applies to the inbound sidecar of the `http` service. This ensures that the headers are removed even if the service is accessed directly from within the mesh, bypassing the gateway.

## Test Cases

To test this configuration, you can perform the following checks:

1.  **Access the service from outside the cluster:**
    *   Send a request to the service through the Istio gateway.
    *   Inspect the response headers.
    *   **Expected result:** The `server`, `x-envoy-upstream-service-time`, and `x-powered-by` headers should not be present in the response.

2.  **Access the service from within the mesh:**
    *   From another pod within the mesh, send a request directly to the `http` service.
    *   Inspect the response headers.
    *   **Expected result:** The `server`, `x-envoy-upstream-service-time`, and `x-powered-by` headers should not be present in the response.