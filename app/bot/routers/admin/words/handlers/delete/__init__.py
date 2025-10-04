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

    if word_type == WordType.keyword:
        title_words = "Ключ-слова"
    elif word_type == WordType.stopword:
        title_words = "Стоп-слова"
    elif word_type == WordType.filter_word:
        title_words = "Фильтр-слова"
    words = await WordRepo.get_all(word_type)
    if not words:
        await cb.answer(f"🤷‍♂️ {title_words} еще не добавлены", show_alert=True)
        return

    await state.update_data(word_type=word_type)
    await state.set_state(WordState.delete_word)

    if word_type == WordType.keyword:
        await cb.message.edit_text(
            "🗑 Пожалуйста, отправьте ключ-слова, которые нужно удалить:",
            reply_markup=Markup.delete_all_words(word_type),
        )
    elif word_type == WordType.stopword:
        await cb.message.edit_text(
            "🗑 Пожалуйста, отправьте стоп-слова, которые нужно удалить:",
            reply_markup=Markup.delete_all_words(word_type),
        )
    elif word_type == WordType.filter_word:
        await cb.message.edit_text(
            "🗑 Пожалуйста, отправьте фильтр-слова, которые нужно удалить:",
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

    if word_type == WordType.keyword:
        deleted_words = await WordRepo.delete_many(words, word_type)
    elif word_type == WordType.stopword:
        deleted_words = await WordRepo.delete_many(words, word_type)
    elif word_type == WordType.filter_word:
        deleted_words = await WordRepo.delete_many(words, word_type)

    await message.answer(
        response_template.format(deleted_words=plural_value(len(deleted_words), PluralType.word)),
        reply_markup=Markup.back_menu(word_type),
    )
