from tortoise import fields
from tortoise.models import Model
from app.enums import WordType


class Word(Model):
    id = fields.IntField(pk=True)  # noqa

    title = fields.CharField(max_length=255)
    normalized_title = fields.CharField(max_length=255)

    word_type = fields.CharEnumField(WordType)

    central_chat_id = fields.BigIntField()

    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now_add=True)

    @property
    def formatted_created_at(self) -> str:
        return self.created_at.strftime("%d.%m.%y %H:%M")
