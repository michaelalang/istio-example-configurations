#!/bin/bash
set -e

echo "Making sysctl settings persistent for Podman kind cluster..."
sudo sh -c 'cat <<EOF > /etc/sysctl.d/99-kind-podman.conf
kernel.keys.maxkeys=10000
kernel.keys.maxbytes=2000000
EOF'
sudo sysctl --system

echo "Setting up kind cluster with podman..."
export KIND_EXPERIMENTAL_PROVIDER=podman

# 1. Create the cluster (using rootful podman so host can route to it)
sudo KIND_EXPERIMENTAL_PROVIDER=podman /home/milang/bin/kind create cluster --config kind-config.yaml --name openshiftanwendertreffen

# Copy kubeconfig to user's home directory so kubectl works without sudo
mkdir -p ~/.kube
sudo cp /root/.kube/config ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config

# 2. Get the podman network subnet for kind (using sudo)
SUBNET=$(sudo podman network inspect kind | jq -r '.[0].subnets[] | select(.subnet | contains(".")) | .subnet')
PREFIX=$(echo $SUBNET | cut -d. -f1-3)
IP_RANGE="${PREFIX}.200-${PREFIX}.250"

echo "Podman kind network subnet: $SUBNET"
echo "Configuring MetalLB with IP range: $IP_RANGE"

# 3. Install MetalLB
echo "Installing MetalLB..."
kubectl apply -f metallb-native.yml

echo "Waiting for MetalLB pods to be ready..."
kubectl wait --namespace metallb-system \
                --for=condition=ready pod \
                --selector=app=metallb \
                --timeout=120s

# 4. Configure MetalLB IPAddressPool and L2Advertisement
cat <<EOF > metallb-config.yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: first-pool
  namespace: metallb-system
spec:
  addresses:
  - ${IP_RANGE}
---
apiVersion: metallb.io/v1beta1
kind: L2Advertisement
metadata:
  name: example
  namespace: metallb-system
EOF

echo "Applying MetalLB configuration..."
kubectl apply -f metallb-config.yaml

# 5. Install cert-manager
echo "Installing cert-manager..."
kubectl apply -f cert-manager.yaml
echo "Waiting for cert-manager pods to be ready..."
kubectl wait --namespace cert-manager \
                --for=condition=ready pod \
                --selector=app.kubernetes.io/instance=cert-manager \
                --timeout=120s

# 6. Install OpenTelemetry Operator
echo "Installing OpenTelemetry Operator..."
kubectl apply -f opentelemetry-operator.yaml
echo "Waiting for OpenTelemetry Operator pods to be ready..."
kubectl wait --namespace opentelemetry-operator-system \
                --for=condition=ready pod \
                --selector=app.kubernetes.io/name=opentelemetry-operator \
                --timeout=120s

# 7.0 required NAD
cat <<EOF | kubectl apply -f-
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: network-attachment-definitions.k8s.cni.cncf.io
spec:
  group: k8s.cni.cncf.io
  scope: Namespaced
  names:
    plural: network-attachment-definitions
    singular: network-attachment-definition
    kind: NetworkAttachmentDefinition
    shortNames:
    - net-attach-def
  versions:
  - name: v1
    served: true
    storage: true
    schema:
      openAPIV3Schema:
        type: object
        properties:
          spec:
            type: object
            x-kubernetes-preserve-unknown-fields: true
            properties:
              config:
                type: string
EOF

# 7.1. Install Istio Sail Operator
echo "Installing Istio Sail Operator..."
kubectl apply --server-side --force-conflicts -f sail-operator.yaml
kubectl apply -k istio
kubectl -n istio-system wait Istio/default --for=condition=Ready --timeout=180s
kubectl -n istio-system wait deploy/istiod --for=condition=Available --timeout=180s

echo "Kind cluster setup complete! MetalLB, cert-manager, OpenTelemetry Operator, and Istio Sail Operator are installed."
