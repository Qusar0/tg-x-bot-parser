from aiogram import Router

from .handlers.menu import router as menu_router
from .handlers.add.business import router as add_router
from .handlers.delete.business import router as delete_router
from .handlers.show.template import router as show_router
from .handlers.rating import router as rating_router
from .handlers.winrate import router as winrate_router

router = Router()

router.include_router(menu_router)
router.include_router(add_router)
router.include_router(delete_router)
router.include_router(show_router)
router.include_router(rating_router)
router.include_router(winrate_router)

