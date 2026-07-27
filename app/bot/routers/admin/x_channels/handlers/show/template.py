from aiogram import Router, types
from aiogram.types import BufferedInputFile

from app.bot.routers.admin.x_channels.Markup import Markup
from app.database.repo.XChannel import XChannelRepo
from app.database.repo.Chat import ChatRepo
from app.bot.callback_data import x_channels_show_cb, x_channels_uploading_cb, XChannelsShowNavCb

router = Router()


PAGE_SIZE = 15


async def _render_page(page: int = 0):
    """
    Возвращает текст списка и актуальную страницу с учетом границ.
    """
    channels = await XChannelRepo.get_all()
    central_chats = await ChatRepo.get_central_chats()
    central_map = {chat.telegram_id: chat for chat in central_chats}

    total = len(channels)
    max_page = max((total - 1) // PAGE_SIZE, 0)
    safe_page = min(max(page, 0), max_page)

    start = safe_page * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = channels[start:end]

    text = "🔗 <b>Список X каналов</b>\n\n"
    for i, channel in enumerate(chunk, start=start + 1):
        rating_text = f"⭐{channel.rating}" if channel.rating > 0 else "❌"
        central_chat = central_map.get(channel.central_chat_id)
        if central_chat:
            # Используем только название и, при наличии, ссылку, встроенную в текст
            central_link = getattr(central_chat, "link", None)
            if central_link:
                central_text = f"<a href='{central_link}'>{central_chat.title}</a>"
            else:
                central_text = central_chat.title
        else:
            central_text = "❌ не привязан"
        text += f"{i}. <b>{channel.title}</b>\n"
        text += f"   URL: {channel.url}\n"
        text += f"   Рейтинг: {rating_text}\n"
        text += f"   Центральный чат: {central_text}\n"
        text += f"   Добавлен: {channel.formatted_created_at}\n\n"

    return text, total, safe_page


@router.callback_query(lambda c: c.data == x_channels_show_cb)
async def show_x_channels_handler(callback: types.CallbackQuery):
    text, total, page = await _render_page(page=0)

    if total == 0:
        await callback.message.edit_text(
            "🔗 <b>Список X каналов</b>\n\n"
            "❌ Список каналов пуст",
            reply_markup=Markup.back_menu()
        )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=Markup.show_x_channels_nav(total=total, page=page, page_size=PAGE_SIZE),
        )
    
    await callback.answer()


@router.callback_query(XChannelsShowNavCb.filter())
async def show_x_channels_nav_handler(callback: types.CallbackQuery, callback_data: XChannelsShowNavCb):
    page = callback_data.page
    if callback_data.direction == "left":
        page -= 1
    elif callback_data.direction == "right":
        page += 1

    text, total, safe_page = await _render_page(page=page)
    await callback.answer()

    await callback.message.edit_text(
        text,
        reply_markup=Markup.show_x_channels_nav(total=total, page=safe_page, page_size=PAGE_SIZE),
    )


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

