import logging
import time
from collections import deque

logger = logging.getLogger(__name__)

API_QUEUE_SIZE = 10
API_WINDOW_SIZE = 60

def apply_api_rate_limit(
    request_times: deque[float],
    max_requests: int = API_QUEUE_SIZE,
    window_seconds: int = API_WINDOW_SIZE
) -> None:
    """
    Sliding window API rate limiter
    Core logic: Maintain a deque of request timestamps; block and wait when the
    number of requests within the sliding window exceeds the rate limit,
    preventing third-party API throttling.

    Args:
        request_times (collections.deque[float]): Deque storing request timestamps.
            Must be initialized externally (global or singleton) and reused across
            calls. Timestamps are typically time.time() values.
        max_requests (int): Maximum allowed number of requests within the sliding
            window.
        window_seconds (int, optional): Sliding window duration in seconds.
            Defaults to 60 (1 minute).

    Returns:
        None: Blocks and waits until the next request is permitted when the rate
            limit is exceeded.

    Raises:
        None: This implementation handles rate limiting via blocking rather than
            raising exceptions.
    """
    def clear_expired(current_time):
        while request_times and current_time - request_times[0] >= window_seconds:
            request_times.popleft()

    current_time = time.time()

    # clear expired requests within the window
    clear_expired(current_time)

    if len(request_times) >= max_requests:
        # calculate the time to wait (window total time - elapsed time of the earliest request)
        sleep_duration = window_seconds - (current_time - request_times[0])
        if sleep_duration > 0:
            logger.warning(f"Triggered API rate limit, window {window_seconds}s has a maximum of {max_requests} requests, need to wait: {sleep_duration:.2f}s")
            time.sleep(sleep_duration)
            # clear expired requests on wakeup
            current_time = time.time()
            clear_expired(current_time)

    request_times.append(current_time)
    logger.info(f"API request time stamp has been recorded, current {window_seconds}s window request count: {len(request_times)}")