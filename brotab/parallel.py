import asyncio
from concurrent.futures import ThreadPoolExecutor


def call_parallel(functions):
    """
    Call functions in multiple threads.

    Create a pool of thread as large as the number of functions.
    Functions should accept no parameters (wrap then with partial or lambda).
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    executor = ThreadPoolExecutor(max_workers=len(functions))

    try:
        tasks = [
            loop.run_in_executor(executor, function)
            for function in functions
        ]
        result = loop.run_until_complete(asyncio.gather(*tasks))

    finally:
        executor.shutdown(wait=True)

    return result
