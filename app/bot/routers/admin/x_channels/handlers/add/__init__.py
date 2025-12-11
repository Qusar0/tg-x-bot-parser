# X Channels add handlers
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from app.bot.routers.admin.x_channels.State import XChannelStates
from app.bot.routers.admin.x_channels.Markup import Markup
from app.bot.callback_data import x_channels_choose_add_cb, x_channels_add_cb, x_channels_add_excel_cb, ChatsCentralChooseCb
from app.database.repo.XChannel import XChannelRepo
from .business import router as business_router

router = Router()
router.include_router(business_router)


@router.callback_query(lambda c: c.data == x_channels_choose_add_cb)
async def choose_add_x_channels_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🔗 <b>Добавление X каналов</b>\n\n"
        "Выберите способ добавления:",
        reply_markup=Markup.choose_add_x_channels()
    )
    await callback.answer()


@router.callback_query(
    F.data.in_([x_channels_add_cb, x_channels_add_excel_cb])
)
async def choose_target_handler_for_x_channels(cb: types.CallbackQuery, state: FSMContext):
    add_type = cb.data
    await state.update_data(add_type=add_type)
    
    await state.set_state(XChannelStates.choose_central_chat)
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer(
        """
🎯 <b>Сначала выберите чат, куда будут приходить уведомления:</b>
""",
        reply_markup=await Markup.choose_central_chats(),
    )
    await cb.answer()


@router.callback_query(ChatsCentralChooseCb.filter(), XChannelStates.choose_central_chat)
async def on_target_chosen_for_x_channels(cb: types.CallbackQuery, callback_data: ChatsCentralChooseCb, state: FSMContext):
    await state.update_data(target_chat_id=callback_data.chat_id)
    
    data = await state.get_data()
    add_type = data.get('add_type')
    
    if add_type == x_channels_add_cb:
        await state.set_state(XChannelStates.waiting_for_manual_input)
        await cb.message.edit_reply_markup(reply_markup=None)
        await cb.message.answer(
            "🔗 <b>Добавление X каналов вручную</b>\n\n"
            "Введите название канала и ссылку:\n"
            "Например: SpaceX https://x.com/SpaceX\n"
            "Или: West (Scarlett's Dad) https://x.com/MarlonTag",
            reply_markup=Markup.cancel_action()
        )
    elif add_type == x_channels_add_excel_cb:
        # Для Excel показываем шаблон
        from .excel_routes import add_x_channels_excel_handler
        await add_x_channels_excel_handler(cb, state)
    await cb.answer()
