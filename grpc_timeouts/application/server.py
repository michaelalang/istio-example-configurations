import time
import grpc
from concurrent import futures
import logging

import timeout_test_pb2
import timeout_test_pb2_grpc

class TimeoutTesterServicer(timeout_test_pb2_grpc.TimeoutTesterServicer):
    def TestTimeout(self, request, context):
        sleep_time = request.sleep_seconds
        logging.info(f"Received request. Sleeping for {sleep_time} seconds...")
        
        # Simulate slow processing
        time.sleep(sleep_time)
        
        # Check if the client already cancelled or timed out before we finish
        if not context.is_active():
            logging.warning("Context is no longer active. Client may have timed out.")
            return timeout_test_pb2.TimeoutResponse(message="Aborted")

        logging.info("Waking up and sending response.")
        return timeout_test_pb2.TimeoutResponse(
            message=f"Success! Slept for {sleep_time} seconds."
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    timeout_test_pb2_grpc.add_TimeoutTesterServicer_to_server(
        TimeoutTesterServicer(), server
    )
    port = "0.0.0.0:50051"
    server.add_insecure_port(port)
    server.start()
    logging.info(f"Server started, listening on {port}")
    server.wait_for_termination()

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    serve()
