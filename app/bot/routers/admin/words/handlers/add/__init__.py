from aiogram import types
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.routers.admin.words.State import WordState
from app.bot.routers.admin.words.Markup import Markup
from app.bot.routers.admin.words.helpers import extract_words
from app.database.repo.Word import WordRepo
from app.enums import WordType
from app.bot.utils.plural import plural_value, PluralType
from app.bot.callback_data import ChooseCentralChatForWordCb, WordMenuAddCb, WordManualAddCb
from app.settings import settings
from . import excel_upload  # noqa


@admin_router.callback_query(WordMenuAddCb.filter())
async def add_word_handler(cb: types.CallbackQuery, callback_data: WordMenuAddCb, state: FSMContext):
    word_type = callback_data.word_type

    await state.update_data(word_type=word_type)
    await state.set_state(WordState.add_word)

    central_chats = settings.get_central_chats()
    if not central_chats:
        await cb.answer("⚠️ Пожалуйста, сначала добавьте чаты для переотправки", show_alert=True)
        return

    word_type_name = "ключевых слов" if word_type == WordType.keyword else "стоп-слов"
    
    await cb.message.edit_text(
        f"📝 <b>Добавление {word_type_name}</b>\n\n"
        f"Выберите способ добавления:",
        reply_markup=Markup.choose_add_words(word_type)
    )
    await cb.answer()


@admin_router.callback_query(WordManualAddCb.filter())
async def manual_add_handler(cb: types.CallbackQuery, callback_data: WordManualAddCb, state: FSMContext):
    word_type = callback_data.word_type

    await state.update_data(word_type=word_type)
    await state.set_state(WordState.add_word)

    if word_type == WordType.keyword:
        await cb.message.edit_text(
            "💬 В какой чат добавить ключ-слова ?", reply_markup=Markup.choose_central_chat(word_type)
        )
    elif word_type == WordType.stopword:
        await cb.message.edit_text(
            "💬 В какой чат добавить стоп-слова ?", reply_markup=Markup.choose_central_chat(word_type)
        )
    await cb.answer()


@admin_router.callback_query(ChooseCentralChatForWordCb.filter(), WordState.add_word)
async def choose_central_chat(cb: types.CallbackQuery, callback_data: ChooseCentralChatForWordCb, state: FSMContext):
    await state.update_data(central_chat_id=callback_data.chat_id)
    word_type = callback_data.word_type

    if word_type == WordType.keyword:
        await cb.message.edit_text(
            "🔑 Пожалуйста, отправьте новые ключ-слова:",
            reply_markup=Markup.back_menu(word_type),
        )
    elif word_type == WordType.stopword:
        await cb.message.edit_text(
            "🛑 Пожалуйста, отправьте стоп-слова для добавления:",
            reply_markup=Markup.back_menu(word_type),
        )


@admin_router.message(WordState.add_word)
async def add_word_scene(message: types.Message, state: FSMContext):
    data = await state.get_data()

    word_type = data["word_type"]
    central_chat_id = data["central_chat_id"]

    words = extract_words(message.text)
    response_template = "<b>{added_words} добавлено в чат: {chat_title} ✅</b>\n<u>Вернитесь назад или добавьте еще:</u>"

    central_chat = next(filter(lambda chat: chat.chat_id == central_chat_id, settings.get_central_chats()))

    if word_type == WordType.stopword:
        added_words = await WordRepo.add_many(words, word_type, central_chat_id)
    elif word_type == WordType.keyword:
        added_words = await WordRepo.add_many(words, word_type, central_chat_id)

    await message.answer(
        response_template.format(
            added_words=plural_value(len(added_words), PluralType.word),
            chat_title=central_chat.title,
        ),
        reply_markup=Markup.back_menu(word_type),
    )
