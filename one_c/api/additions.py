import time

from urllib3 import Retry


class RetryWithDelay(Retry):
    def __init__(self, *args, delay: int = 0, **kwargs):
        self.delay = delay
        super().__init__(*args, **kwargs)

    def increment(self, *args, **kwargs):
        if self.delay > 0:
            time.sleep(self.delay)
        return super().increment(*args, **kwargs)
