from aiogram import types
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import WordShowCb
from app.database.repo.Word import WordRepo
from app.bot.routers.admin.words.Markup import Markup
from app.enums import WordType
from .template import get_words_template


@admin_router.callback_query(WordShowCb.filter())
async def show_words(cb: types.CallbackQuery, callback_data: WordShowCb, state: FSMContext):
    await state.set_state(None)
    word_type = callback_data.word_type

    words = await WordRepo.get_all(word_type)
    if word_type == WordType.keyword:
        title_words = "Ключ-слова"
    elif word_type == WordType.stopword:
        title_words = "Стоп-слова"
    elif word_type == WordType.filter_word:
        title_words = "Фильтр-слова"

    if not words:
        await cb.answer(f"🤷‍♂️ {title_words} еще не добавлены", show_alert=True)
        return

    raw_template, html_template = get_words_template(words, word_type)

    await cb.answer()

    if len(raw_template) <= 4096:
        await cb.message.edit_text(
            html_template,
            reply_markup=Markup.back_menu(word_type),
        )
    else:
        await cb.message.answer_document(
            types.BufferedInputFile(raw_template.encode(), filename=f"Текущие {title_words}.txt")
        )
