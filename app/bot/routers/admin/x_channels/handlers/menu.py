from aiogram import Router, types
from aiogram.filters import Command
from app.bot.routers.admin.x_channels.Markup import Markup

router = Router()


@router.message(Command("x_channels"))
async def x_channels_menu_handler(message: types.Message):
    await message.answer(
        "🔗 <b>Управление X каналами</b>\n\n"
        "Выберите действие:",
        reply_markup=Markup.x_channels_menu()
    )

