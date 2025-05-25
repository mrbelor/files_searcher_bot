from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from .bot_config import TEXTS, TAG_LABELS

def report_keyboard(report_id: str, page_idx: int, total: int, doc_id) -> InlineKeyboardMarkup:
    """
    Собирает клавиатуру для перелистывания отчёта:
    ⬅ [текущая/всего] ➡
    """
    # Кнопки «вперёд/назад» и прогресс
    if page_idx > 0:
        btn_prev = InlineKeyboardButton(TEXTS['previous_button'], callback_data=f"rep_{report_id}_{page_idx-1}")
    else:
        btn_prev = InlineKeyboardButton(TEXTS['noop_button'], callback_data="noop")

    btn_index = InlineKeyboardButton(f"{page_idx+1}/{total}", callback_data="noop")

    if page_idx < total - 1:
        btn_next = InlineKeyboardButton(TEXTS['next_button'], callback_data=f"rep_{report_id}_{page_idx+1}")
    else:
        btn_next = InlineKeyboardButton(" ", callback_data="noop")
    
    download = InlineKeyboardButton(TEXTS['download_button'], callback_data=f"download:{doc_id}")

    kb = InlineKeyboardMarkup()
    kb.row(btn_prev, btn_index, btn_next) # все три кнопки в одной строке.
    kb.row(download)                      # и ещё кнопка ниже.

    return kb

# === В markup.py ===

def kb_initial(filters: dict):
    current = ",\n".join(f" * {TAG_LABELS[k]} = {v}" for k, v in filters.items()) or TEXTS["empty_filters"]
    caption = TEXTS["ask_filters"].format(current=current)
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(TEXTS["add_filters"],   callback_data="filters:start"),
        InlineKeyboardButton(TEXTS["clear_filters"], callback_data="filters:clear"),
    )
    kb.add(
        InlineKeyboardButton(TEXTS["done"],   callback_data="filters:done"),
        InlineKeyboardButton(TEXTS["cancel"], callback_data="filters:cancel"),
    )
    return caption, kb


def kb_choose_tag():
    kb = InlineKeyboardMarkup(row_width=2)
    for key, label in TAG_LABELS.items():
        if key == "date": # (все кроме date)
            continue
        kb.add(InlineKeyboardButton(label, callback_data=f"filters:tag:{key}"))
    kb.add(InlineKeyboardButton(TEXTS["back"], callback_data="filters:back"))
    return kb


def kb_values(tag: str, values: list):
    kb = InlineKeyboardMarkup(row_width=2)
    # теперь callback_data – это индекс, а не сама строка
    for i, v in enumerate(values):
        kb.add(
            InlineKeyboardButton(v, callback_data=f"filters:value:{tag}:{i}")
        )
    kb.add( InlineKeyboardButton(TEXTS["back"], callback_data="filters:back") )
    return kb
