from aiogram import types
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.routers.admin.words.State import WordState
from app.bot.routers.admin.words.Markup import Markup
from app.bot.routers.admin.words.helpers import extract_words
from app.database.repo.Word import WordRepo
from app.enums import WordType
from app.bot.utils.plural import PluralType
from app.bot.callback_data import DeleteAllWordsCb, WordMenuDeleteCb
from app.bot.utils.plural import plural_value


@admin_router.callback_query(WordMenuDeleteCb.filter())
async def delete_words(cb: types.CallbackQuery, callback_data: WordMenuDeleteCb, state: FSMContext):
    word_type = callback_data.word_type

    # Определяем название и платформу
    is_keyword = word_type in [WordType.tg_keyword, WordType.x_keyword]
    is_stopword = word_type in [WordType.tg_stopword, WordType.x_stopword]
    is_filter_word = word_type in [WordType.tg_filter_word, WordType.x_filter_word]
    
    platform = "TG" if word_type.value.startswith("tg_") else "X"
    
    if is_keyword:
        title_words = f"Ключ-слова {platform}"
    elif is_stopword:
        title_words = f"Стоп-слова {platform}"
    elif is_filter_word:
        title_words = f"Фильтр-слова {platform}"
    words = await WordRepo.get_all(word_type)
    if not words:
        await cb.answer(f"🤷‍♂️ {title_words} еще не добавлены", show_alert=True)
        return

    await state.update_data(word_type=word_type)
    await state.set_state(WordState.delete_word)

    if is_keyword:
        await cb.message.edit_text(
            f"🗑 Пожалуйста, отправьте ключ-слова {platform}, которые нужно удалить:",
            reply_markup=Markup.delete_all_words(word_type),
        )
    elif is_stopword:
        await cb.message.edit_text(
            f"🗑 Пожалуйста, отправьте стоп-слова {platform}, которые нужно удалить:",
            reply_markup=Markup.delete_all_words(word_type),
        )
    elif is_filter_word:
        await cb.message.edit_text(
            f"🗑 Пожалуйста, отправьте фильтр-слова {platform}, которые нужно удалить:",
            reply_markup=Markup.delete_all_words(word_type),
        )


@admin_router.callback_query(DeleteAllWordsCb.filter())
async def delete_all_words(cb: types.CallbackQuery, state: FSMContext, callback_data: DeleteAllWordsCb):
    word_type = callback_data.word_type

    await state.set_state(None)

    words = await WordRepo.get_all(word_type)
    deleted_words_count = await WordRepo.bulk_delete(words)

    response_template = f"<b>{plural_value(deleted_words_count, PluralType.word)} удалено ✔️</b>\n"
    await cb.message.edit_text(response_template, reply_markup=Markup.back_menu(word_type))


@admin_router.message(WordState.delete_word)
async def delete_words_scene(message: types.Message, state: FSMContext):
    data = await state.get_data()
    word_type = data["word_type"]

    words = extract_words(message.text)
    response_template = "<b>{deleted_words} удалено ✔️</b>\n<u>Вернитесь назад или удалите еще:</u>"

    # Удаляем слова для любого типа
    deleted_words = await WordRepo.delete_many(words, word_type)

    await message.answer(
        response_template.format(deleted_words=plural_value(len(deleted_words), PluralType.word)),
        reply_markup=Markup.back_menu(word_type),
    )
