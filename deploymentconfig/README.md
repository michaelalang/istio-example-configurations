# Istio with OpenShift DeploymentConfig

This use case demonstrates how to use Istio with OpenShift `DeploymentConfig` objects.

**NOTE** DeploymentConfig is deprecated and target to be removed from OpenShift.

## Summary

This example shows a simple `httpd` application deployed using an OpenShift `DeploymentConfig`. The key aspect of this use case is to illustrate how the Istio sidecar is injected into the `DeploymentConfig`'s pod template.

*   `deploymentconfig.yml`: This file contains the original `DeploymentConfig` for the `httpd` application, before the Istio sidecar is injected. It's a standard OpenShift `DeploymentConfig`.
*   `deploymentconfig-injected.yml`: This file shows the same `DeploymentConfig` after the Istio sidecar injector has modified it. You can see the addition of the `istio-proxy` container and the `istio-init` init container, along with the necessary volumes and environment variables.

This example is useful for understanding how Istio works with OpenShift-specific resources like `DeploymentConfig`.

You can use upstream **istioctl** to update your deploymentconfig yaml with the injection

```
istioctl kube-inject deploymentConfig.yaml
```

## Test Cases

To test this configuration, you can perform the following checks:

1.  **Deploy the `DeploymentConfig`:**
    *   Apply the `deploymentconfig.yml` file to your OpenShift cluster.
    *   Verify that the `httpd` pod is running.
    *   Access the `httpd` service through the OpenShift Route and Istio Gateway.
    *   **Expected result:** You should see the `httpd` welcome page.

2.  **Verify sidecar injection:**
    *   Inspect the running `httpd` pod and verify that the `istio-proxy` container is present and running.
    *   Check the pod's logs to ensure that the sidecar is communicating with the Istio control plane.
    *   **Expected result:** The pod should have two containers: `container` and `istio-proxy`.

3.  **Traffic management:**
    *   You can apply Istio traffic management resources like `VirtualService` and `DestinationRule` to the `httpd` service to further test Istio's functionality.
    *   For example, you could create a `VirtualService` to route traffic to a different version of the `httpd` application.
    *   **Expected result:** The traffic should be routed according to the rules you define in the `VirtualService`.
