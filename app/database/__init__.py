from app.config import config

TORTOISE_ORM = {
    "connections": {"default": config.db.uri},
    "apps": {
        "models": {
            "models": ["app.database.models", "aerich.models"],
            "default_connection": "default",
        },
    },
}
