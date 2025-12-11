import re
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.bot.routers.admin.x_channels.Markup import Markup
from app.bot.routers.admin.x_channels.State import XChannelStates
from app.bot.routers.admin.x_channels.phrases import cancel_chat_action
from app.database.repo.XChannel import XChannelRepo
from app.bot.callback_data import x_channels_choose_add_cb, x_channels_add_cb, x_channels_add_excel_cb, x_channels_cb, ChatsCentralChooseCb
from aiogram import F
from .excel_routes import router as excel_router

router = Router()
router.include_router(excel_router)


@router.callback_query(lambda c: c.data == x_channels_cb)
async def back_to_x_channels_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🔗 <b>X каналы</b>\n\n"
        "Управление каналами X для мониторинга",
        reply_markup=Markup.x_channels_menu()
    )
    await callback.answer()


@router.message(XChannelStates.waiting_for_manual_input)
async def process_manual_x_channel_input(message: types.Message, state: FSMContext):
    if message.text == cancel_chat_action:
        await message.answer("🚫 Отменено", reply_markup=Markup.remove())
        await state.clear()
        return

    try:
        text = message.text.strip()
        
        # Ищем URL в тексте (начинается с http или x.com)
        url_pattern = r'(https?://[^\s]+|x\.com/[^\s]+)'
        url_match = re.search(url_pattern, text)
        
        if not url_match:
            await message.answer(
                "❌ Неверный формат. Введите название и ссылку:\n"
                "Например: SpaceX https://x.com/SpaceX",
                reply_markup=Markup.back_menu()
            )
            return
        
        url = url_match.group(1)
        title = text[:url_match.start()].strip()
        
        if not title:
            await message.answer(
                "❌ Неверный формат. Введите название и ссылку:\n"
                "Например: SpaceX https://x.com/SpaceX",
                reply_markup=Markup.back_menu()
            )
            return
        
        # Проверяем, что URL начинается с http
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Проверяем, что канал не существует
        existing_channel = await XChannelRepo.get_by_url(url)
        if existing_channel:
            await message.answer(
                f"❌ Канал с URL {url} уже существует",
                reply_markup=Markup.back_menu()
            )
            return

        # Получаем central_chat_id из state
        data = await state.get_data()
        central_chat_id = data.get('target_chat_id')
        
        # Добавляем канал
        channel = await XChannelRepo.add(title, url, central_chat_id=central_chat_id)
        # await message.answer()
        current_rating = f"Текущий рейтинг: {channel.rating} ⭐" if channel.rating > 0 else "Текущий рейтинг: ❌ не оценён"

        await message.answer(
            f"<b>🏆 Оценка X канала</b>\n\n"
            f"<b>Канал:</b> {channel.title}\n"
            f"<b>URL:</b> {channel.url}\n"
            f"<b>{current_rating}</b>\n\n"
            "Выберите новый рейтинг от 1 до 10:",
            reply_markup=Markup.rating_keyboard(channel.id)
        )
        await state.set_state(XChannelStates.add_raiting_winrate)
        # await message.answer(
        #     f"✅ Канал <b>{channel.title}</b> добавлен!\n"
        #     f"URL: {channel.url}",
        #     reply_markup=Markup.back_menu()
        # )
        
        # await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении X канала: {e}")
        await message.answer(
            "❌ Произошла ошибка при добавлении канала",
            reply_markup=Markup.back_menu()
        )
