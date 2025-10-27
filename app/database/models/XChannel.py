from tortoise import fields
from tortoise.models import Model


class XChannel(Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=255)
    url = fields.CharField(max_length=500)
    rating = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)

    @property
    def formatted_created_at(self) -> str:
        return self.created_at.strftime("%d.%m.%y %H:%M")

