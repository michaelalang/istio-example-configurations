# Sidecar Memory Consumption

This use case is designed to demonstrate how the size and complexity of the Istio configuration can impact the memory consumption of the sidecar proxies.

## Summary

In this scenario, we have a simple `httpd` service. The key element is the `vs2.yml` file, which contains a very large `VirtualService` with hundreds of individual routes. When this `VirtualService` is applied to the mesh, Istio will propagate the configuration to all the sidecar proxies that need to know about it.

The purpose of this use case is to observe the memory usage of the `istio-proxy` container in the `http` pod before and after applying the large `VirtualService`. This will illustrate the direct relationship between the amount of configuration in the mesh and the amount of memory required by the sidecars.

This is an important consideration when designing and managing a service mesh, as a large and complex configuration can lead to significant memory overhead in the sidecars, which can impact the overall performance and resource utilization of your applications.

## Test Cases

To test this configuration, you can perform the following checks:

1.  **Deploy the base configuration:**
    *   Apply all the configuration files in the `istio` directory except for `vs2.yml`.
    *   Wait for the `http` pod to be running.
    *   Check the memory usage of the `istio-proxy` container in the `http` pod. You can use a command like `kubectl top pod <pod-name> -n <namespace> --containers`.
    *   **Expected result:** You should see a baseline memory usage for the sidecar.

2.  **Apply the large `VirtualService`:**
    *   Apply the `vs2.yml` file.
    *   Wait for the configuration to be propagated to the sidecars.
    *   Check the memory usage of the `istio-proxy` container in the `http` pod again.
    *   **Expected result:** You should see a significant increase in the memory usage of the sidecar compared to the baseline.

3.  **Remove the large `VirtualService`:**
    *   Delete the `vs2.yml` file.
    *   Wait for the configuration to be removed from the sidecars.
    *   Check the memory usage of the `istio-proxy` container in the `http` pod one more time.
    *   **Expected result:** The memory usage of the sidecar should return to the baseline level.