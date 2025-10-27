from aiogram import Router, types
from loguru import logger

from app.bot.routers.admin.x_channels.Markup import Markup
from app.database.repo.XChannel import XChannelRepo
from app.bot.callback_data import x_channels_remove_cb, XChannelDeleteCb

router = Router()


@router.callback_query(lambda c: c.data == x_channels_remove_cb)
async def remove_x_channels_handler(callback: types.CallbackQuery):
    channels = await XChannelRepo.get_all()
    
    if not channels:
        await callback.message.edit_text(
            "🔗 <b>Удаление X каналов</b>\n\n"
            "❌ Список каналов пуст",
            reply_markup=Markup.back_menu()
        )
    else:
        await callback.message.edit_text(
            "🔗 <b>Удаление X каналов</b>\n\n"
            "Выберите канал для удаления:",
            reply_markup=await Markup.remove_x_channels()
        )
    
    await callback.answer()


@router.callback_query(XChannelDeleteCb.filter())
async def delete_x_channel_handler(callback: types.CallbackQuery, callback_data: XChannelDeleteCb):
    try:
        channel = await XChannelRepo.get_by_id(callback_data.channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден")
            return

        success = await XChannelRepo.delete(callback_data.channel_id)
        if success:
            await callback.message.edit_text(
                f"✅ Канал <b>{channel.title}</b> удален!",
                reply_markup=await Markup.remove_x_channels()
            )
        else:
            await callback.answer("❌ Ошибка при удалении канала")
            
    except Exception as e:
        logger.error(f"Ошибка при удалении X канала: {e}")
        await callback.answer("❌ Произошла ошибка при удалении канала")
    
    await callback.answer()

