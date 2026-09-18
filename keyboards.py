from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ---------- Главное меню ----------

def main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🔥 Смотреть анкеты")],
        [KeyboardButton(text="👤 Моя анкета"), KeyboardButton(text="✏️ Изменить анкету")],
        [KeyboardButton(text="⏸ Скрыть анкету"), KeyboardButton(text="▶️ Показывать анкету")],
    ]
    if is_admin:
        rows.append([KeyboardButton(text="🛠 Админ-панель")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def gender_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Мужской"), KeyboardButton(text="Женский")]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def looking_for_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Мужчин"), KeyboardButton(text="Женщин")],
            [KeyboardButton(text="Всех")],
        ],
        resize_keyboard=True, one_time_keyboard=True,
    )


# ---------- Просмотр анкет ----------

def rating_kb(target_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💔", callback_data=f"react:dislike:{target_id}"),
            InlineKeyboardButton(text="❤️", callback_data=f"react:like:{target_id}"),
        ],
        [InlineKeyboardButton(text="🚩 Пожаловаться", callback_data=f"report:{target_id}")],
    ])


# ---------- Админ-панель ----------

def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
        [InlineKeyboardButton(text="📋 Последние пользователи", callback_data="adm:list_users")],
        [InlineKeyboardButton(text="🚩 Открытые жалобы", callback_data="adm:reports")],
        [InlineKeyboardButton(text="🔨 Заблокировать пользователя", callback_data="adm:ban")],
        [InlineKeyboardButton(text="✅ Разблокировать пользователя", callback_data="adm:unban")],
        [InlineKeyboardButton(text="⏸ Выключить анкету", callback_data="adm:disable")],
        [InlineKeyboardButton(text="▶️ Включить анкету", callback_data="adm:enable")],
        [InlineKeyboardButton(text="🚀 Бустить свою анкету", callback_data="adm:boost_self")],
        [InlineKeyboardButton(text="❤️ Накрутить себе лайки", callback_data="adm:fake_likes_self")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="adm:broadcast")],
    ])


def report_action_kb(report_id: int, reported_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔨 Забанить нарушителя", callback_data=f"adm:ban_from_report:{report_id}:{reported_id}"),
            InlineKeyboardButton(text="✅ Отклонить жалобу", callback_data=f"adm:dismiss_report:{report_id}"),
        ]
    ])


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="❌ Отмена")]], resize_keyboard=True)


def broadcast_confirm_kb() -> ReplyKeyboardMarkup:
    """Появляется только на время подготовки рассылки, в общее меню не входит."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Разослать"), KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True, one_time_keyboard=True,
    )
