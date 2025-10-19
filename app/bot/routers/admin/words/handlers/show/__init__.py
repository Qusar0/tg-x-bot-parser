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
    
    # Определяем название и платформу
    is_keyword = word_type in [WordType.tg_keyword]
    is_stopword = word_type in [WordType.tg_stopword]
    is_filter_word = word_type in [WordType.tg_filter_word]
    
    platform = "TG" if word_type.value.startswith("tg_") else "X"
    
    if is_keyword:
        title_words = f"Ключ-слова {platform}"
    elif is_stopword:
        title_words = f"Стоп-слова {platform}"
    elif is_filter_word:
        title_words = f"Фильтр-слова {platform}"

    if not words:
        await cb.answer(f"🤷‍♂️ {title_words} еще не добавлены", show_alert=True)
        return

    raw_template, html_template = await get_words_template(words, word_type)

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
