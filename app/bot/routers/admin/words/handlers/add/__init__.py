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
from app.database.repo.Chat import ChatRepo
from app.bot.routers.admin.words.handlers.add import excel_routes  # noqa


@admin_router.callback_query(WordMenuAddCb.filter())
async def add_word_handler(cb: types.CallbackQuery, callback_data: WordMenuAddCb, state: FSMContext):
    word_type = callback_data.word_type

    await state.update_data(word_type=word_type)
    await state.set_state(WordState.add_word)

    central_chats = await ChatRepo.get_central_chats()
    if not central_chats:
        await cb.answer("⚠️ Пожалуйста, сначала добавьте чаты для переотправки", show_alert=True)
        return

    # Определяем название и платформу
    is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
    is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
    is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
    
    platform = "TG" if word_type.value.startswith("tg_") else "X"
    
    if is_keyword:
        word_type_name = f"ключевых слов {platform}"
    elif is_stopword:
        word_type_name = f"стоп-слов {platform}"
    elif is_filter_word:
        word_type_name = f"фильтр-слов {platform}"

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

    # Определяем название и платформу
    is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
    is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
    is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
    
    platform = "TG" if word_type.value.startswith("tg_") else "X"
    
    if is_keyword:
        await cb.message.edit_text(
            f"💬 В какой чат добавить ключ-слова {platform}?", reply_markup=await Markup.choose_central_chat(word_type)
        )
    elif is_stopword:
        await cb.message.edit_text(
            f"💬 В какой чат добавить стоп-слова {platform}?", reply_markup=await Markup.choose_central_chat(word_type)
        )
    elif is_filter_word:
        await cb.message.edit_text(
            f"💬 В какой чат добавить фильтр-слова {platform}?", reply_markup=await Markup.choose_central_chat(word_type)
        )
    await cb.answer()


@admin_router.callback_query(ChooseCentralChatForWordCb.filter(), WordState.add_word)
async def choose_central_chat(cb: types.CallbackQuery, callback_data: ChooseCentralChatForWordCb, state: FSMContext):
    await state.update_data(central_chat_id=callback_data.chat_id)
    word_type = callback_data.word_type

    # Определяем название и платформу
    is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
    is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
    is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
    
    platform = "TG" if word_type.value.startswith("tg_") else "X"
    
    if is_keyword:
        await cb.message.edit_text(
            f"🔑 Пожалуйста, отправьте новые ключ-слова {platform}:",
            reply_markup=Markup.back_menu(word_type),
        )
    elif is_stopword:
        await cb.message.edit_text(
            f"🛑 Пожалуйста, отправьте стоп-слова {platform} для добавления:",
            reply_markup=Markup.back_menu(word_type),
        )
    elif is_filter_word:
        await cb.message.edit_text(
            f"🔍 Пожалуйста, отправьте фильтр-слова {platform} для добавления:",
            reply_markup=Markup.back_menu(word_type),
        )


@admin_router.message(WordState.add_word)
async def add_word_scene(message: types.Message, state: FSMContext):
    data = await state.get_data()

    word_type = data["word_type"]
    central_chat_id = data["central_chat_id"]

    words = extract_words(message.text)
    response_template = "<b>{added_words} добавлено в чат: {chat_title} ✅</b>\n{skipped_note}<u>Вернитесь назад или добавьте еще:</u>"

    from app.database.repo.Chat import ChatRepo
    central_chat = await ChatRepo.get_by_telegram_id(central_chat_id)

    # Добавляем слова для любого типа
    added_words = await WordRepo.add_many(words, word_type, central_chat_id)

    skipped_count = len(words) - len(added_words)
    skipped_note = f"⚠️ Пропущено (уже есть в этом чате): {skipped_count}\n" if skipped_count else ""

    await message.answer(
        response_template.format(
            added_words=plural_value(len(added_words), PluralType.word),
            chat_title=central_chat.title,
            skipped_note=skipped_note,
        ),
        reply_markup=Markup.back_menu(word_type),
    )
