# Egress Database Connectivity

This use case demonstrates how to control egress traffic from the service mesh to an external database, in this case, a PostgreSQL database running on AWS RDS.

## Summary

This scenario addresses the common requirement of securely connecting to an external database from within the service mesh. The key components of this configuration are:

*   **ServiceEntry:** A `ServiceEntry` is used to register the external database's hostname (`css-perf-pg.cajxzvn40anb.us-east-2.rds.amazonaws.com`) with Istio's service registry. This allows us to treat the external service as if it were a service within the mesh.
*   **Egress Gateway:** An egress gateway is deployed to act as a controlled exit point for traffic leaving the mesh. All traffic to the external database will be routed through this gateway.
*   **VirtualService:** The `VirtualService` is configured to intercept traffic destined for the external database and route it to the egress gateway. It also handles the routing from the egress gateway to the final destination.
*   **DestinationRule:** A `DestinationRule` is used to define a subset for the egress gateway service, which is then used in the `VirtualService`.
*   **AuthorizationPolicy:** An `AuthorizationPolicy` is applied to the egress gateway to restrict which clients are allowed to connect to the external database. In this example, it only allows traffic from `127.0.0.1`, which is likely a placeholder for a more realistic source.

This setup provides a secure and controlled way to manage egress traffic to external services, which is a critical aspect of a zero-trust network architecture.

## Test Cases

To test this configuration, you can perform the following checks:

1.  **Connect to the database from an authorized source:**
    *   From a pod that is allowed by the `AuthorizationPolicy`, attempt to connect to the external database using its hostname.
    *   **Expected result:** The connection should be successful.

2.  **Connect to the database from an unauthorized source:**
    *   From a pod that is not allowed by the `AuthorizationPolicy`, attempt to connect to the external database.
    *   **Expected result:** The connection should be denied.

3.  **Verify traffic flows through the egress gateway:**
    *   Check the logs of the egress gateway pod to confirm that it is receiving and forwarding traffic to the external database.
    *   **Expected result:** You should see log entries indicating that the egress gateway is proxying the database connection.