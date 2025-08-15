from tortoise import fields
from tortoise.models import Model


class Chat(Model):
    telegram_id = fields.BigIntField(pk=True)
    title = fields.CharField(max_length=255)
    entity = fields.CharField(max_length=255, null=True)

    messages_count = fields.IntField(default=0)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now_add=True)

    @property
    def link(self) -> str:
        if self.entity:
            if "@" in self.entity:
                entity = self.entity.replace("@", "")
                return f"https://t.me/{entity}"

            return self.entity

        return str(self.telegram_id)

    @property
    def formatted_created_at(self) -> str:
        return self.created_at.strftime("%d.%m.%y %H:%M")
