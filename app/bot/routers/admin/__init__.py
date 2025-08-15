from app.bot.utils.Router import Router
from app.bot.routers import root_handlers_router

admin_router = Router()

root_handlers_router.include_router(admin_router)
