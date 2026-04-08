import io
import json
import uuid
import zipfile
import aiohttp
from app.config import config
from loguru import logger


class N8NClient:
    def __init__(self):
        self.webhook_url = config.n8n.check_channel_webhook_url
        self.timeout_seconds = int(config.n8n.check_channel_timeout_seconds)
        self.shared_secret = config.n8n.check_channel_shared_secrets

    async def send_posts_batch(self, channel: str, posts: list[dict], media_files: dict[str, bytes] | None = None) -> dict:
        if not self.webhook_url:
            raise RuntimeError("N8N_CHECK_WEBHOOK_URL is not set")

        request_id = str(uuid.uuid4())
        bundle_bytes = self._build_bundle_zip(
            channel=channel,
            request_id=request_id,
            posts=posts,
            media_files=media_files or {},
        )

        headers = {
            "Content-Type": "application/zip",
        }
        if self.shared_secret:
            headers["X-Internal-Secret"] = self.shared_secret
        headers["X-Request-Id"] = request_id
        headers["X-Channel"] = channel

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

        logger.info(
            "Отправка zip bundle в n8n | channel={} | posts_count={} | media_count={}",
            channel,
            len(posts),
            len(media_files or {}),
        )

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.webhook_url, data=bundle_bytes, headers=headers) as response:
                text = await response.text()

                logger.info(
                    "Ответ от n8n | status={} | body={}",
                    response.status,
                    text,
                )

                if response.status != 200:
                    raise RuntimeError(f"n8n returned status {response.status}: {text}")
                return await response.json()

    @staticmethod
    def _build_bundle_zip(
        channel: str,
        request_id: str,
        posts: list[dict],
        media_files: dict[str, bytes],
    ) -> bytes:
        buffer = io.BytesIO()

        manifest = {
            "channel": channel,
            "request_id": request_id,
            "posts": posts,
        }

        with zipfile.ZipFile(buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )

            for filename, content in media_files.items():
                zip_path = filename
                if not zip_path.startswith("media/"):
                    zip_path = f"media/{zip_path}"
                zf.writestr(zip_path, content)

        buffer.seek(0)
        return buffer.getvalue()
