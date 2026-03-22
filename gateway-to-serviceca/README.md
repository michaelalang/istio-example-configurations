# Gateway TLS Configuration: Passthrough vs. Re-encryption

This use case demonstrates two different ways to configure the Istio gateway to handle TLS traffic: TLS passthrough and TLS termination with re-encryption. It also shows how to use the service CA to secure the connection between the gateway and the backend service.

## Summary

This scenario provides a practical comparison of two common TLS configurations at the gateway.

### TLS Passthrough

In the passthrough scenario, the gateway does not terminate the TLS connection. Instead, it forwards the encrypted traffic directly to the backend service.

*   **Gateway Configuration:** The gateway is configured with `tls: mode: PASSTHROUGH`.
*   **DestinationRule Configuration:** The `DestinationRule` for the backend service is configured with `tls: mode: DISABLE`. This is because the service itself is responsible for terminating the TLS connection, and the gateway should not attempt to create a TLS connection to it.
*   **Use Case:** This approach is useful when you want to offload TLS termination to the backend service, or when you have specific security requirements that prevent the gateway from decrypting the traffic.

#### Deployment

* execute following command to deploy the passthrough configuration

```
oc apply -k passthrough
```

### TLS Re-encryption

In the re-encryption scenario, the gateway terminates the TLS connection from the client and then re-encrypts the traffic before forwarding it to the backend service.

*   **Gateway Configuration:** The gateway is configured with `tls: mode: SIMPLE` and a `credentialName`, which specifies the server certificate to be used for TLS termination.
*   **DestinationRule Configuration:** The `DestinationRule` for the backend service is configured with `tls: mode: SIMPLE` and a `caCertificates` path pointing to the service CA certificate. This tells the gateway to initiate a new TLS connection to the backend service and to trust the service's certificate if it's signed by the service CA.
*   **Use Case:** This approach is useful when you want to centralize TLS termination at the gateway, which can simplify certificate management and reduce the load on backend services. It also allows you to inspect the traffic at the gateway for security or routing purposes.

#### Deployment

* execute following command to deploy the reencryption configuration

```
oc apply -k reencrypt
```

## Test Cases

To test this configuration, you can perform the following checks:

### Passthrough

1.  **Access the service using a client that trusts the service's certificate:**
    *   Send a request to the passthrough host (`http-passthrough.apps.example.com`) using a client that is configured to trust the certificate of the backend service.
    *   **Expected result:** The request should be successful, and the connection should be end-to-end encrypted.

### Re-encryption

1.  **Access the service using a client that trusts the gateway's certificate:**
    *   Send a request to the re-encryption host (`http.apps.example.com`) using a client that is configured to trust the gateway's certificate.
    *   **Expected result:** The request should be successful. The connection between the client and the gateway will be encrypted with the gateway's certificate, and the connection between the gateway and the backend service will be encrypted with the service's certificate.