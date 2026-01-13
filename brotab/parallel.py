from concurrent.futures import ThreadPoolExecutor
from asyncio import get_event_loop, gather, new_event_loop, set_event_loop

def call_parallel(functions):
    """
    Call functions in multiple threads.

    Create a pool of thread as large as the number of functions.
    Functions should accept no parameters (wrap then with partial or lambda).
    """

    try:
      loop = get_event_loop()
      if loop.is_closed():
        raise RuntimeError("Event loop is closed.")
    except RuntimeError:
      loop = new_event_loop()
      set_event_loop(loop)

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
