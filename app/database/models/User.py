from tortoise import fields
from tortoise.models import Model


class User(Model):
    id = fields.IntField(pk=True)  # noqa
    telegram_id = fields.BigIntField(unique=True, null=True)

    full_name = fields.CharField(max_length=255, null=True)
    username = fields.CharField(max_length=255, null=True)

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now_add=True)

    @property
    def formatted_created_at(self) -> str:
        return self.created_at.strftime("%d.%m.%y %H:%M")

    @property
    def exists_entity(self) -> str:
        return f"@{self.username}" if self.username else str(self.telegram_id)

    @property
    def exists_link_entity(self) -> str:
        return f"https://t.me/{self.username}" if self.username else ""
