from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "xchannel" ADD "rating" INT NOT NULL DEFAULT 0;
        """


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "xchannel" DROP COLUMN "rating";
        """
