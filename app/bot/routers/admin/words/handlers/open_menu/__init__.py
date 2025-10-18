from aiogram import types
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import WordMenuCb
from app.enums import WordType
from app.bot.routers.admin.words.Markup import Markup


def get_keywords_menu_template() -> str:
    return '<b>Перешли в меню ключ-слов</b> 🔑'


@admin_router.callback_query(WordMenuCb.filter())
async def words_menu(cb: types.CallbackQuery, callback_data: WordMenuCb, state: FSMContext):
    await state.set_state(None)
    word_type = callback_data.word_type

    # Telegram слова
    if word_type == WordType.tg_keyword:
        await cb.message.edit_text(
            "<b>🔑 Ключ-слова для Telegram</b>",
            reply_markup=Markup.open_menu(WordType.tg_keyword),
        )
    elif word_type == WordType.tg_stopword:
        await cb.message.edit_text(
            "<b>🛑 Стоп-слова для Telegram</b>",
            reply_markup=Markup.open_menu(WordType.tg_stopword),
        )
    elif word_type == WordType.tg_filter_word:
        await cb.message.edit_text(
            "<b>🔍 Фильтр-слова для Telegram</b>",
            reply_markup=Markup.open_menu(WordType.tg_filter_word),
        )
    # X слова
    elif word_type == WordType.x_keyword:
        await cb.message.edit_text(
            "<b>🔑 Ключ-слова для X</b>",
            reply_markup=Markup.open_menu(WordType.x_keyword),
        )
    elif word_type == WordType.x_stopword:
        await cb.message.edit_text(
            "<b>🛑 Стоп-слова для X</b>",
            reply_markup=Markup.open_menu(WordType.x_stopword),
        )
    elif word_type == WordType.x_filter_word:
        await cb.message.edit_text(
            "<b>🔍 Фильтр-слова для X</b>",
            reply_markup=Markup.open_menu(WordType.x_filter_word),
        )
