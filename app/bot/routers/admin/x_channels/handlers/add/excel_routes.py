from aiogram import Router, types
from aiogram.types import BufferedInputFile
from loguru import logger

from app.bot.routers.admin.x_channels.Markup import Markup
from app.bot.routers.admin.x_channels.handlers.add.loading_excel_x_channel import ExcelXChannelParser
from app.database.repo.XChannel import XChannelRepo
from app.bot.callback_data import x_channels_add_excel_cb

router = Router()


@router.callback_query(lambda c: c.data == x_channels_add_excel_cb)
async def add_x_channels_excel_handler(callback: types.CallbackQuery):
    # Отправляем шаблон Excel файла
    template_data = ExcelXChannelParser.create_template_excel()
    
    await callback.message.edit_text(
        "📗 <b>Загрузка X каналов из Excel</b>\n\n"
        "Скачайте шаблон Excel файла и заполните его данными каналов.\n"
        "Затем отправьте заполненный файл.",
        reply_markup=Markup.back_menu()
    )
    
    await callback.message.answer_document(
        BufferedInputFile(
            template_data,
            filename="x_channels_template.xlsx"
        ),
        caption="📗 <b>Шаблон для загрузки X каналов</b>\n\n"
                "Заполните файл и отправьте его обратно."
    )
    
    await callback.answer()


@router.message(lambda m: m.document and m.document.file_name.endswith(('.xlsx', '.xls')))
async def process_x_channels_excel_file(message: types.Message):
    try:
        # Скачиваем файл
        file = await message.bot.get_file(message.document.file_id)
        file_content = await message.bot.download_file(file.file_path)
        
        # Парсим Excel файл
        channels, errors = ExcelXChannelParser.parse_excel_file(file_content.read())
        
        if errors:
            error_text = "❌ <b>Ошибки в файле:</b>\n\n" + "\n".join(errors)
            if len(error_text) > 4096:
                await message.answer_document(
                    BufferedInputFile(
                        error_text.encode('utf-8'),
                        filename="errors.txt"
                    ),
                    caption="❌ <b>Ошибки в Excel файле</b>"
                )
            else:
                await message.answer(error_text)
            return
        
        if not channels:
            await message.answer("❌ В файле не найдено корректных данных")
            return
        
        # Добавляем каналы в базу данных
        added_count = 0
        skipped_count = 0
        
        for channel_data in channels:
            try:
                # Проверяем, не существует ли уже такой канал
                existing_channel = await XChannelRepo.get_by_url(channel_data['link'])
                if existing_channel:
                    skipped_count += 1
                    logger.info(f"Канал {channel_data['name']} уже существует, пропускаем")
                    continue
                
                # Добавляем канал
                await XChannelRepo.add(channel_data['name'], channel_data['link'])
                added_count += 1
                logger.info(f"Добавлен канал: {channel_data['name']} - {channel_data['link']}")
                
            except Exception as e:
                logger.error(f"Ошибка при добавлении канала {channel_data['name']}: {e}")
                skipped_count += 1
        
        # Отправляем результат
        result_text = (
            f"✅ <b>Загрузка завершена!</b>\n\n"
            f"📊 <b>Результат:</b>\n"
            f"• Добавлено: {added_count}\n"
            f"• Пропущено: {skipped_count}\n"
            f"• Всего обработано: {len(channels)}"
        )
        
        await message.answer(result_text)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке Excel файла: {e}")
        await message.answer("❌ Произошла ошибка при обработке файла")

