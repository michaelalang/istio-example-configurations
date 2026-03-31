import os
import grpc
import logging
import timeout_test_pb2
import timeout_test_pb2_grpc

def run():
    # Target port updated to 80 as a default for plain HTTP/2 gRPC traffic
    target = os.environ.get("GRPC_TARGET", "127.0.0.1:50051")
    server_sleep_seconds = int(os.environ.get("SLEEP_S", 20))
    client_timeout_seconds = int(os.environ.get("SLEEP_C", 15))

    logging.info(f"Connecting to {target}...")

    # Connect using an insecure channel (plaintext)
    with grpc.insecure_channel(target) as channel:
        stub = timeout_test_pb2_grpc.TimeoutTesterStub(channel)
        
        try:
            logging.info(f"Calling server: Asking to sleep for {server_sleep_seconds}s, Client timeout is {client_timeout_seconds}s.")
            
            response = stub.TestTimeout(
                timeout_test_pb2.TimeoutRequest(sleep_seconds=server_sleep_seconds),
                timeout=client_timeout_seconds
            )
            logging.info(f"Response received: {response.message}")
            
        except grpc.RpcError as e:
            # 1. Client-side timeout (e.g., SLEEP_C is shorter than SLEEP_S and the Envoy proxy timeout)
            if e.code() == grpc.StatusCode.DEADLINE_EXCEEDED:
                logging.error(f"Client-side Timeout Triggered! DEADLINE_EXCEEDED: {e.details()}")
            
            # 2. Server or Proxy issues (gRPC maps HTTP 502/503/504 to UNAVAILABLE)
            elif e.code() == grpc.StatusCode.UNAVAILABLE:
                details = e.details().lower()
                if "upstream request timeout" in details:
                    # Envoy hit the VirtualService timeout and returned HTTP 504
                    logging.error(f"Istio Proxy Timeout (HTTP 504 Gateway Timeout): {e.details()}")
                elif "connection refused" in details:
                    # Envoy couldn't reach the pod, or nothing is listening on the port
                    logging.error(f"Connection Refused (Check Service targetPort/containerPort): {e.details()}")
                elif "connection reset" in details:
                    # Usually a TLS handshake failure or protocol mismatch
                    logging.error(f"Connection Reset (Likely a TLS/Protocol mismatch): {e.details()}")
                else:
                    # Generic fallback
                    logging.error(f"Service Unavailable (HTTP 503): {e.details()}")
            
            # 3. Catch-all for other gRPC errors
            else:
                logging.error(f"RPC failed: Status Code {e.code()} - {e.details()}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    run()
