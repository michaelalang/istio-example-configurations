# Use TinyGo 0.33.0 (supports Go 1.22/1.23)
FROM docker.io/tinygo/tinygo:0.33.0 AS builder

USER 0
WORKDIR /src

# Copy module files first for caching
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY main.go .

# Build flags optimized for Envoy
# -scheduler=none: Crucial for performance in Proxy-Wasm (single-threaded)
# -target=wasi: Required for Envoy
RUN tinygo build -o /src/main.wasm -scheduler=none -target=wasi -no-debug main.go

# Export stage
FROM scratch
ENV DELAY_MS=1000
COPY --from=builder /src/main.wasm /plugin.wasm
