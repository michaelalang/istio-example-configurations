# ==========================================
# Stage 1: Builder
# ==========================================
FROM registry.access.redhat.com/ubi10/ubi-minimal AS builder

# Install Python, pip, and core build tools. 
# (grpcio usually provides pre-compiled wheels, but build tools ensure fallback compilation works)
RUN microdnf install -y python3 python3-pip python3-devel gcc gcc-c++ && \
    microdnf clean all

WORKDIR /build

# Create a virtual environment to isolate dependencies.
# This makes it incredibly easy to copy the exact python payload to the final image.
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install gRPC runtime and compiler tools
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir grpcio grpcio-tools

# Copy application and proto files
COPY timeout_test.proto server.py client.py ssl_client.py ./

# Compile the Protocol Buffer into Python files
RUN python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. timeout_test.proto


# ==========================================
# Stage 2: Final Minimal Image
# ==========================================
FROM registry.access.redhat.com/ubi10/ubi-minimal

# Install ONLY the Python 3 runtime without weak dependencies (no pip, no dev tools)
RUN microdnf install -y --setopt=install_weak_deps=0 python3 && \
    microdnf clean all

WORKDIR /app

# Copy the populated virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Set PATH to use the copied virtual environment
ENV PATH="/opt/venv/bin:$PATH"

# Copy ONLY the necessary application scripts and the compiled protobuf python files.
# The original .proto file is intentionally left behind.
COPY --from=builder /build/server.py \
                    /build/client.py \
                    /build/ssl_client.py \
                    /build/timeout_test_pb2.py \
                    /build/timeout_test_pb2_grpc.py \
                    ./

# OpenShift Best Practice: Ensure the container runs as a non-root user (UID 1001)
# and grant the root group (0) execution/read rights to support arbitrary UIDs.
RUN chown -R 1001:0 /app && chmod -R g=u /app
USER 1001

# Expose the gRPC port
EXPOSE 50051

# Start the server by default
CMD ["python", "server.py"]
