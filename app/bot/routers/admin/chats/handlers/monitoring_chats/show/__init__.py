from aiogram import types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin import admin_router
from app.bot.callback_data import chats_show_cb, ChatsShowNavCb
from app.database.repo.Chat import ChatRepo
from app.bot.routers.admin.chats.Markup import Markup
from app.bot.routers.admin.chats.template import get_chats_template


PAGE_SIZE = 15


async def _render_page(page: int = 0):
    """
    Возвращает шаблоны и актуальную страницу.
    Корректирует page, если он выходит за пределы.
    """
    chats = await ChatRepo.get_all()
    central_chats = await ChatRepo.get_central_chats()
    central_map = {chat.telegram_id: chat for chat in central_chats}

    total = len(chats)
    max_page = max((total - 1) // PAGE_SIZE, 0)
    safe_page = min(max(page, 0), max_page)

    start = safe_page * PAGE_SIZE
    end = start + PAGE_SIZE
    chunk = chats[start:end]

    raw_template, html_template = get_chats_template(
        chunk,
        central_map=central_map,
        start_index=start,
    )
    return raw_template, html_template, total, safe_page


@admin_router.callback_query(F.data == chats_show_cb)
async def chats_show(cb: types.CallbackQuery, state: FSMContext):
    await state.set_state(None)

    raw_template, html_template, total, page = await _render_page(page=0)

    if total == 0:
        await cb.answer("🤷‍♂️ Чаты еще не добавлены", show_alert=True)
        return

    await cb.answer()

    await cb.message.edit_text(
        html_template,
        reply_markup=Markup.show_chats_nav(total=total, page=page, page_size=PAGE_SIZE),
    )


@admin_router.callback_query(ChatsShowNavCb.filter())
async def chats_show_nav(cb: types.CallbackQuery, callback_data: ChatsShowNavCb, state: FSMContext):
    await state.set_state(None)

    direction = callback_data.direction
    page = callback_data.page
    if direction == "left":
        page -= 1
    elif direction == "right":
        page += 1

    raw_template, html_template, total, safe_page = await _render_page(page=page)
    await cb.answer()

    await cb.message.edit_text(
        html_template,
        reply_markup=Markup.show_chats_nav(total=total, page=safe_page, page_size=PAGE_SIZE),
    )
