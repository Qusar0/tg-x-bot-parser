from aiogram.filters.callback_data import CallbackData
from app.enums import WordType

settings_cb = "settings"
filters_cb = "filters"
back_menu_cb = "back-menu"
delete_cb = "delete"

# Парсеры
tg_parser_cb = "tg-parser"
x_parser_cb = "x-parser"

# X каналы
x_channels_cb = "x-channels"
x_channels_add_cb = "x-channels-add"
x_channels_choose_add_cb = "x-channels-choose-add"
x_channels_add_excel_cb = "x-channels-add-excel"
x_channels_remove_cb = "x-channels-remove"
x_channels_show_cb = "x-channels-show"
x_channels_uploading_cb = "x-channels-excel"
x_channels_rating_cb = "x-channels-rating"
x_channels_without_rating_cb = "x-channels-without-rating"
x_channels_re_evaluation_cb = "x-channels-re-evaluation"

# Чаты
chats_cb = "chats"
chats_monitorings_cb = "chats-monitorings"
chats_central_cb = "chats-central"
chats_show_cb = "show-chats"
chats_add_cb = "add-chats"
chats_choose_add_cb = "choose-add-chats"
chats_add_excel_cb = "add-chats-excel"
chats_remove_cb = "remove-chats"
chats_uploading_cb = "chats-excel"

chats_central_add_cb = "add-central-chats"
chats_central_remove_cb = "remove-central-chats"
chats_central_add_me_cb = "add-me-central-chats"

chats_load_from_account = "chats-load-from-account"

chats_change_rating_cb = "chats-change-rating"
chats_without_rating_cb = "chats-without-rating"
chats_re_evaluation_cb = "chats-re-evaluation"


class ChatRatingCb(CallbackData, prefix="cr"):
    chat_id: int
    rating: int


class ChooseCentralChatForWordCb(CallbackData, prefix="pqt-1"):
    word_type: WordType
    chat_id: int


class ChatsCentralDeleteCb(CallbackData, prefix="clv"):
    chat_id: int


class ChooseChatCb(CallbackData, prefix="l-m-a-t-d"):
    chat_id: int
    page: int
    is_choose: bool = False


chats_add_loaded_chat_cb = "chats-load-add-chat"


class NavigationChatCb(CallbackData, prefix="oitg"):
    direction: str
    page: int


class ChangeSettingsCb(CallbackData, prefix="att"):
    field: str
    value: bool


class ChangeFiltersCb(CallbackData, prefix="cft"):
    field: str
    value: bool


class WordMenuCb(CallbackData, prefix="wm"):
    word_type: WordType


class WordMenuAddCb(CallbackData, prefix="wa"):
    word_type: WordType


class WordMenuDeleteCb(CallbackData, prefix="wd"):
    word_type: WordType


class DeleteAllWordsCb(CallbackData, prefix="daw"):
    word_type: WordType


class WordShowCb(CallbackData, prefix="ws"):
    word_type: WordType


class WordUploadingCb(CallbackData, prefix="wu"):
    word_type: WordType


class WordExcelLoadCb(CallbackData, prefix="wel"):
    word_type: WordType


class WordManualAddCb(CallbackData, prefix="wma"):
    word_type: WordType


class ChooseChatForExcelCb(CallbackData, prefix="cce"):
    word_type: WordType
    chat_id: int


class XChannelDeleteCb(CallbackData, prefix="xcd"):
    channel_id: int


class XChannelRatingCb(CallbackData, prefix="xcr"):
    channel_id: int
    rating: int
