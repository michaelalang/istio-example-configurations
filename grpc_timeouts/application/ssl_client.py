import os
import grpc
import logging
import timeout_test_pb2
import timeout_test_pb2_grpc

def run():
    target = os.environ.get("GRPC_TARGET", "127.0.0.1:50051")
    server_sleep_seconds = int(os.environ.get("SLEEP_S", 20))
    client_timeout_seconds = int(os.environ.get("SLEEP_C", 15))
    
    # Define the path to your extracted CA cert
    ca_cert_path = os.environ.get("CA_CERT_PATH", "ca.crt")

    logging.info(f"Connecting securely to {target}...")

    # 1. Load the custom CA Certificate
    try:
        with open(ca_cert_path, 'rb') as f:
            trusted_certs = f.read()
    except FileNotFoundError:
        logging.error(f"Could not find CA certificate at '{ca_cert_path}'. gRPC requires this to verify the TLS connection.")
        return

    # 2. Create the SSL credentials
    credentials = grpc.ssl_channel_credentials(root_certificates=trusted_certs)

    # 3. Override the SNI hostname (Crucial for Istio ingress routing via IP)
    # This tells gRPC to verify the cert against 'grpc.apps.example.com' instead of '127.0.0.1'
    options = (
        ('grpc.ssl_target_name_override', 'grpc.apps.example.com'),
    )

    # 4. Connect using the secure channel and options
    with grpc.secure_channel(target, credentials, options=options) as channel:
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
