# Coraza WAF at the Gateway

This use case demonstrates how to use the Coraza WasmPlugin as a Web Application Firewall (WAF) at the Istio gateway.

**NOTE** The coraza WAF is fully unsupported by Red Hat.

## Summary

In this scenario, we apply a `WasmPlugin` with the Coraza WAF image to the Istio gateway. The WAF is configured with a set of rules to inspect incoming requests and deny them if they match certain criteria. The specific rules configured in this example are:

*   Deny requests to `/admin`.
*   Deny requests with `curl` in the `User-Agent` header.
*   Deny requests with `192.168.192.37` in the `x-forwarded-for` header.
*   Log requests from `127.0.0.1`.

The `WasmPlugin` is configured to run in the `AUTHN` phase, which means it will be executed before any Istio authentication policies.

## Test Cases

To test this configuration, you can perform the following checks:

1.  **Accessing a blocked URI:**
    *   Send a request to `http.apps.example.com/admin`.
    *   **Expected result:** The request should be denied with a 403 Forbidden status code.

2.  **Using a blocked User-Agent:**
    *   Send a request to `http.apps.example.com` with the `User-Agent` header set to `curl/7.68.0`.
    *   **Expected result:** The request should be denied.

3.  **From a blocked IP address:**
    *   Send a request to `http.apps.example.com` with the `x-forwarded-for` header set to `192.168.192.37`.
    *   **Expected result:** The request should be denied.

4.  **From a whitelisted IP address:**
    *   Send a request to `http.apps.example.com` from `127.0.0.1`.
    *   **Expected result:** The request should be allowed, and a log entry should be created.

5.  **Normal access:**
    *   Send a request to `http.apps.example.com` from a non-blocked IP address with a normal User-Agent.
    *   **Expected result:** The request should be allowed.