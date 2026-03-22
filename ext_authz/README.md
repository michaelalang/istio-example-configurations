# External Authorization with OAuth2-Proxy and Dex

This use case demonstrates how to integrate an external authorization service, `oauth2-proxy`, with Istio's `ext_authz` mechanism. Dex is used as the OpenID Connect (OIDC) provider.

## Summary

This scenario provides a complete example of how to secure your service mesh with a robust authentication and authorization solution. The key components are:

*   **Dex:** Dex is an identity service that uses OpenID Connect to drive authentication for other apps. In this example, Dex is configured with a static user and a client application.
*   **OAuth2-Proxy:** `oauth2-proxy` is a reverse proxy and static file server that provides authentication using providers like Google, GitHub, and others. Here, it's configured to use Dex as its OIDC provider. It also uses Redis for session storage.
*   **Istio `ext_authz`:** The Istio mesh is configured to use `oauth2-proxy` as an external authorization provider. This is done by defining an `extensionProvider` in the `Istio` custom resource. This configuration tells Istio to forward incoming requests to `oauth2-proxy` for an authorization decision before routing them to the intended service.

When a user tries to access a service in the mesh, the request is first intercepted by the Istio gateway. The gateway then sends the request to `oauth2-proxy` for authorization. If the user is not authenticated, `oauth2-proxy` redirects them to the Dex login page. After successful authentication, `oauth2-proxy` sets a session cookie and allows the request to proceed to the service.

## Deployment

* adjust your Istio CR with the `extensionProvider` seen in `istio.yml`
* execute following command to deploy oauth2-proxy and a protected example httpd application

```
oc create -k .
```

## Test Cases

To test this configuration, you can perform the following checks:

1.  **Access a protected service without being authenticated:**
    *   Open a new browser window in incognito mode and try to access a service behind the Istio gateway.
    *   **Expected result:** You should be redirected to the Dex login page.

2.  **Log in with valid credentials:**
    *   On the Dex login page, enter the credentials for the static user defined in the Dex configuration (`test@example.com` / `password`).
    *   **Expected result:** After successful authentication, you should be redirected back to the original service, and the service should be accessible.

3.  **Access the service again:**
    *   In the same browser session, try to access the service again.
    *   **Expected result:** You should be able to access the service without being prompted to log in again, as you have a valid session cookie.

4.  **Log out and try to access the service:**
    *   Clear your browser's cookies or use a different browser session.
    *   Try to access the service again.
    *   **Expected result:** You should be redirected to the Dex login page again.