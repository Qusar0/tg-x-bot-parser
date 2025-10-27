from aiogram import Router, types
from aiogram.types import BufferedInputFile

from app.bot.routers.admin.x_channels.Markup import Markup
from app.database.repo.XChannel import XChannelRepo
from app.bot.callback_data import x_channels_show_cb, x_channels_uploading_cb

router = Router()


@router.callback_query(lambda c: c.data == x_channels_show_cb)
async def show_x_channels_handler(callback: types.CallbackQuery):
    channels = await XChannelRepo.get_all()
    
    if not channels:
        await callback.message.edit_text(
            "🔗 <b>Список X каналов</b>\n\n"
            "❌ Список каналов пуст",
            reply_markup=Markup.back_menu()
        )
    else:
        channels_text = "🔗 <b>Список X каналов</b>\n\n"
        
        for i, channel in enumerate(channels, 1):
            rating_text = f"⭐{channel.rating}" if channel.rating > 0 else "❌"
            channels_text += f"{i}. <b>{channel.title}</b>\n"
            channels_text += f"   URL: {channel.url}\n"
            channels_text += f"   Рейтинг: {rating_text}\n"
            channels_text += f"   Добавлен: {channel.formatted_created_at}\n\n"
        
        if len(channels_text) <= 4096:
            await callback.message.edit_text(
                channels_text,
                reply_markup=Markup.back_menu()
            )
        else:
            # Если текст слишком длинный, отправляем как файл
            await callback.message.answer_document(
                BufferedInputFile(
                    channels_text.encode('utf-8'),
                    filename="x_channels_list.txt"
                ),
                reply_markup=Markup.back_menu()
            )
    
    await callback.answer()


@router.callback_query(lambda c: c.data == x_channels_uploading_cb)
async def upload_x_channels_excel_handler(callback: types.CallbackQuery):
    channels = await XChannelRepo.get_all()
    
    if not channels:
        await callback.message.edit_text(
            "📗 <b>Выгрузка X каналов в Excel</b>\n\n"
            "❌ Список каналов пуст",
            reply_markup=Markup.back_menu()
        )
    else:
        # Создаем CSV файл
        csv_content = "ID,Название,URL,Дата добавления\n"
        for channel in channels:
            csv_content += f"{channel.id},{channel.title},{channel.url},{channel.formatted_created_at}\n"
        
        await callback.message.answer_document(
            BufferedInputFile(
                csv_content.encode('utf-8'),
                filename="x_channels.csv"
            ),
            caption="📗 <b>Список X каналов</b>",
            reply_markup=Markup.back_menu()
        )
    
    await callback.answer()

