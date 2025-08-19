import asyncio
import time


class MessageQueue:
    def __init__(self, delay):
        self._delay = delay
        self._queue = []
        self._last_time_sent = 0
        self._is_sending = False

    async def call(self, message):
        self._queue.append(message)
        if not self._is_sending:
            self._is_sending = True
            while self._queue:
                now = int(time.time())

                if (now - self._last_time_sent) >= self._delay:
                    message = self._queue.pop(0)
                    method, *args = message
                    await method(*args)
                    self._last_time_sent = now
                else:
                    wait_time = self._delay - (now - self._last_time_sent)
                    await asyncio.sleep(wait_time)
            self._is_sending = False

    def clear_queue(self):
        self._queue.clear()


queue = MessageQueue(delay=2)
