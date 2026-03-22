# Restrict Access to Specific Paths

This use case demonstrates three different ways to restrict access to specific paths of a service: using an `AuthorizationPolicy`, an `EnvoyFilter` with a Lua script, and a `VirtualService` with `directResponse`.

**Disclaimer:** This scenario uses `EnvoyFilter`, which is not supported by Red Hat for Service Mesh configurations. Using `EnvoyFilter` can have unintended consequences and should be done with extreme caution.

## Summary

This example provides a comparison of three different methods for controlling access to specific URL paths, each with its own trade-offs in terms of complexity, flexibility, and performance.

### `AuthorizationPolicy`

This is the most straightforward and recommended way to perform path-based authorization in Istio.

*   **How it works:** An `AuthorizationPolicy` is configured with a `DENY` action and a rule that specifies a list of `notPaths`. This means that any request whose path is not in the `notPaths` list will be denied.
*   **Pros:** Simple, declarative, and the standard way to do authorization in Istio.
*   **Cons:** Less flexible than the `EnvoyFilter` approach for more complex logic.

### `EnvoyFilter` with Lua

This approach provides the most flexibility by allowing you to write custom logic in a Lua script.

*   **How it works:** An `EnvoyFilter` is used to inject a Lua filter into the HTTP filter chain. The Lua script inspects the request path and returns a 404 Not Found response if the path is not in the allowed list.
*   **Pros:** Extremely flexible; you can implement any logic you want in the Lua script.
*   **Cons:** More complex to write and maintain, and can have a performance impact.

### `VirtualService` with `directResponse`

This approach uses the `directResponse` feature of `VirtualService` to handle unmatched paths.

*   **How it works:** The `VirtualService` is configured with explicit matches for the allowed paths. A final, catch-all route is configured with a `directResponse` that returns a 404 Not Found response.
*   **Pros:** Simple and declarative.
*   **Cons:** Can be verbose if you have a large number of allowed paths, as each path needs to be explicitly matched.

## Test Cases

To test this configuration, you can perform the following checks for each of the three methods:

1.  **Access an allowed path:**
    *   Send a request to one of the allowed paths (e.g., `/2`, `/4`, `/6`, `/8`).
    *   **Expected result:** The request should be successful, and you should receive a response from the backend service.

2.  **Access a denied path:**
    *   Send a request to a path that is not in the allowed list (e.g., `/1`, `/3`, `/5`).
    *   **Expected result:** You should receive a 403 Forbidden response (for the `AuthorizationPolicy` method) or a 404 Not Found response (for the `EnvoyFilter` and `VirtualService` methods).
