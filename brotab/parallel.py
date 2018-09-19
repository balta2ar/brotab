from concurrent.futures import ThreadPoolExecutor
from asyncio import get_event_loop, gather


def call_parallel(functions):
    """
    Call functions in multiple threads.

    Create a pool of thread as large as the number of functions.
    Functions should accept no parameters (wrap then with partial or lambda).
    """
    loop = get_event_loop()
    executor = ThreadPoolExecutor(max_workers=len(functions))

    try:
        tasks = [
            loop.run_in_executor(executor, function)
            for function in functions
        ]
        result = loop.run_until_complete(gather(*tasks))

    finally:
        loop.close()

    return result
