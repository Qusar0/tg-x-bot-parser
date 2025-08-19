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

    if word_type == WordType.keyword:
        await cb.message.edit_text(
            get_keywords_menu_template(),
            reply_markup=Markup.open_menu(WordType.keyword),
        )
    elif word_type == WordType.stopword:
        await cb.message.edit_text(
            "<b>🛑 Перешли в меню стоп-слов</b>",
            reply_markup=Markup.open_menu(WordType.stopword),
        )
