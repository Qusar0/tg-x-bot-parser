import re
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from loguru import logger

from app.bot.routers.admin.x_channels.Markup import Markup
from app.bot.routers.admin.x_channels.State import XChannelStates
from app.bot.routers.admin.x_channels.phrases import cancel_chat_action
from app.database.repo.XChannel import XChannelRepo
from app.bot.callback_data import x_channels_choose_add_cb, x_channels_add_cb, x_channels_add_excel_cb, x_channels_cb
from .excel_routes import router as excel_router

router = Router()
router.include_router(excel_router)


@router.callback_query(lambda c: c.data == x_channels_choose_add_cb)
async def choose_add_x_channels_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔗 <b>Добавление X каналов</b>\n\n"
        "Выберите способ добавления:",
        reply_markup=Markup.choose_add_x_channels()
    )
    await callback.answer()


@router.callback_query(lambda c: c.data == x_channels_add_cb)
async def add_x_channels_manual_handler(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔗 <b>Добавление X каналов вручную</b>\n\n"
        "Введите название канала и ссылку:\n"
        "Например: SpaceX https://x.com/SpaceX\n"
        "Или: West (Scarlett's Dad) https://x.com/MarlonTag",
        reply_markup=Markup.cancel_action()
    )
    await state.set_state(XChannelStates.waiting_for_manual_input)
    await callback.answer()


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

        # Добавляем канал
        channel = await XChannelRepo.add(title, url)
        await message.answer(
            f"✅ Канал <b>{channel.title}</b> добавлен!\n"
            f"URL: {channel.url}",
            reply_markup=Markup.back_menu()
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при добавлении X канала: {e}")
        await message.answer(
            "❌ Произошла ошибка при добавлении канала",
            reply_markup=Markup.back_menu()
        )
