import uuid
import aiohttp
from app.config import config
from loguru import logger


class N8NClient:
    def __init__(self):
        self.webhook_url = config.n8n.check_channel_webhook_url
        self.timeout_seconds = int(config.n8n.check_channel_timeout_seconds)
        self.shared_secret = config.n8n.check_channel_shared_secrets

    async def check_channel(self, channel: str, requested_by: int, chat_id: int) -> dict:
        payload = {
            "channel": channel,
            "requested_by": requested_by,
            "chat_id": chat_id,
            "request_id": str(uuid.uuid4()),
        }
        headers = {
            "Content-Type": "application/json",
            "secret_key": self.shared_secret
        }

        if self.shared_secret:
            headers["X-Internal-Secret"] = self.shared_secret

        logger.info("Отправка запроса в n8n | url={} | payload={}", self.webhook_url, payload)

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.webhook_url, json=payload, headers=headers) as response:
                text = await response.text()

                logger.info(
                    "Ответ от n8n | status={} | body={}",
                    response.status,
                    text,
                )

                if response.status != 200:
                    raise RuntimeError(f"n8n returned status {response.status}: {text}")

                try:
                    return await response.json()
                except Exception as ex:
                    raise RuntimeError(f"Invalid JSON from n8n: {text}") from ex
