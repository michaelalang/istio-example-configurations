import asyncio

def post_fork(server, worker):
    """
    Called just after a worker has been forked.
    Sets a new event loop for the worker process/thread.
    """
    try:
        # Create a new event loop and set it as the current event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        worker.log.info("Asyncio event loop created and set in worker.")
    except Exception as e:
        worker.log.error(f"Error setting asyncio loop: {e}")
