import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InputMediaPhoto

import db
import keyboards as kb
from config import BOT_TOKEN, ADMIN_ID, MIN_AGE, MAX_AGE, BOOST_DURATION_HOURS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ==================== FSM СОСТОЯНИЯ ====================

class Registration(StatesGroup):
    name = State()
    age = State()
    gender = State()
    looking_for = State()
    city = State()
    bio = State()
    photo = State()


class ReportFlow(StatesGroup):
    reason = State()


class AdminFlow(StatesGroup):
    wait_ban_id = State()
    wait_unban_id = State()
    wait_disable_id = State()
    wait_enable_id = State()
    wait_fake_likes_amount = State()
    wait_broadcast_content = State()
    wait_broadcast_confirm = State()


# ==================== СТАРТ / РЕГИСТРАЦИЯ ====================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Если пользователь запустил /start посреди какого-то сценария
    # (регистрация, жалоба и т.п.), сбрасываем застрявшее состояние.
    await state.clear()

    if db.is_banned(message.from_user.id):
        await message.answer("⛔️ Вы заблокированы в этом боте.")
        return

    if db.user_exists(message.from_user.id):
        await message.answer(
            "С возвращением! Выберите действие в меню 👇",
            reply_markup=kb.main_menu(is_admin(message.from_user.id)),
        )
        return

    await state.set_state(Registration.name)
    await message.answer(
        "Добро пожаловать в бота знакомств! 💘\n\n"
        "Давайте создадим вашу анкету.\nКак вас зовут?"
    )


@router.message(Registration.name)
async def reg_name(message: Message, state: FSMContext):
    name = (message.text or "").strip()[:50]
    if not name:
        await message.answer("Имя не может быть пустым. Как вас зовут?")
        return
    await state.update_data(name=name)
    await state.set_state(Registration.age)
    await message.answer(f"Сколько вам лет? (от {MIN_AGE} до {MAX_AGE})")


@router.message(Registration.age)
async def reg_age(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введите возраст цифрами.")
        return
    age = int(message.text)
    if age < MIN_AGE or age > MAX_AGE:
        await message.answer(
            f"К сожалению, регистрация в боте доступна только для пользователей "
            f"от {MIN_AGE} до {MAX_AGE} лет."
        )
        await state.clear()
        return
    await state.update_data(age=age)
    await state.set_state(Registration.gender)
    await message.answer("Ваш пол?", reply_markup=kb.gender_kb())


@router.message(Registration.gender, F.text.in_(["Мужской", "Женский"]))
async def reg_gender(message: Message, state: FSMContext):
    gender = "M" if message.text == "Мужской" else "F"
    await state.update_data(gender=gender)
    await state.set_state(Registration.looking_for)
    await message.answer("Кого хотите видеть в анкетах?", reply_markup=kb.looking_for_kb())


@router.message(Registration.looking_for, F.text.in_(["Мужчин", "Женщин", "Всех"]))
async def reg_looking_for(message: Message, state: FSMContext):
    mapping = {"Мужчин": "M", "Женщин": "F", "Всех": "ALL"}
    await state.update_data(looking_for=mapping[message.text])
    await state.set_state(Registration.city)
    await message.answer("Из какого вы города?", reply_markup=None)


@router.message(Registration.city)
async def reg_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text.strip()[:50])
    await state.set_state(Registration.bio)
    await message.answer("Пару слов о себе (расскажите о своих интересах):")


@router.message(Registration.bio)
async def reg_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text.strip()[:500])
    await state.set_state(Registration.photo)
    await message.answer("Пришлите вашу фотографию для анкеты 📷")


@router.message(Registration.photo, F.photo)
async def reg_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    data = await state.get_data()
    db.create_or_update_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        name=data["name"],
        age=data["age"],
        gender=data["gender"],
        looking_for=data["looking_for"],
        city=data["city"],
        bio=data["bio"],
        photo_id=photo_id,
    )
    await state.clear()
    await message.answer(
        "✅ Анкета создана! Теперь можно смотреть других участников.",
        reply_markup=kb.main_menu(is_admin(message.from_user.id)),
    )


@router.message(Registration.photo)
async def reg_photo_invalid(message: Message):
    await message.answer("Пожалуйста, пришлите именно фотографию 📷")


# ==================== МОЯ АНКЕТА ====================

@router.message(F.text == "👤 Моя анкета")
async def my_profile(message: Message):
    user = db.get_user(message.from_user.id)
    if not user:
        await message.answer("У вас ещё нет анкеты. Введите /start")
        return
    likes = db.get_likes_count(user["id"])
    status = "🟢 активна" if user["is_active"] else "⏸ скрыта"
    caption = (
        f"👤 {user['name']}, {user['age']}\n"
        f"🏙 {user['city']}\n"
        f"📝 {user['bio']}\n\n"
        f"❤️ Лайков получено: {likes}\n"
        f"Статус анкеты: {status}"
    )
    await message.answer_photo(photo=user["photo_id"], caption=caption)


@router.message(F.text == "✏️ Изменить анкету")
async def edit_profile(message: Message, state: FSMContext):
    await state.set_state(Registration.name)
    await message.answer("Хорошо, заполним анкету заново.\nКак вас зовут?")


@router.message(F.text == "⏸ Скрыть анкету")
async def hide_profile(message: Message):
    if not db.user_exists(message.from_user.id):
        await message.answer("У вас ещё нет анкеты. Введите /start")
        return
    db.set_active(message.from_user.id, False)
    await message.answer("Ваша анкета скрыта из показа другим пользователям.")


@router.message(F.text == "▶️ Показывать анкету")
async def show_profile(message: Message):
    if not db.user_exists(message.from_user.id):
        await message.answer("У вас ещё нет анкеты. Введите /start")
        return
    db.set_active(message.from_user.id, True)
    await message.answer("Ваша анкета снова видна другим пользователям.")


# ==================== ПРОСМОТР АНКЕТ ====================

async def send_next_profile(message: Message, viewer_id: int):
    profile = db.get_next_profile(viewer_id)
    if not profile:
        await message.answer("Анкет пока больше нет 🙁 Загляните позже — ждём новых участников!")
        return
    likes = db.get_likes_count(profile["id"])
    caption = (
        f"👤 {profile['name']}, {profile['age']}\n"
        f"🏙 {profile['city']}\n"
        f"📝 {profile['bio']}\n\n"
        f"❤️ Лайков: {likes}"
    )
    await message.answer_photo(
        photo=profile["photo_id"], caption=caption,
        reply_markup=kb.rating_kb(profile["id"]),
    )


@router.message(F.text == "🔥 Смотреть анкеты")
async def browse(message: Message):
    if not db.user_exists(message.from_user.id):
        await message.answer("Сначала создайте анкету: /start")
        return
    if db.is_banned(message.from_user.id):
        await message.answer("⛔️ Вы заблокированы.")
        return
    await send_next_profile(message, message.from_user.id)


def _match_text(name: str, username: str | None) -> str:
    text = f"🎉 Взаимная симпатия! У вас мэтч с {name}."
    if username:
        text += f"\nМожете написать: @{username}"
    return text


@router.callback_query(F.data.startswith("react:"))
async def on_react(callback: CallbackQuery):
    viewer_id = callback.from_user.id
    if db.is_banned(viewer_id):
        await callback.answer("⛔️ Вы заблокированы.", show_alert=True)
        return

    _, reaction, target_id_str = callback.data.split(":")
    target_id = int(target_id_str)

    is_match = db.add_reaction(viewer_id, target_id, reaction)

    await callback.message.delete()

    if reaction == "like" and is_match:
        viewer = db.get_user(viewer_id)
        target = db.get_user(target_id)
        await callback.message.answer(_match_text(target["name"], target["username"]))
        try:
            await callback.bot.send_message(
                target_id, _match_text(viewer["name"], viewer["username"])
            )
        except Exception:
            pass
    elif reaction == "like":
        try:
            await callback.bot.send_message(
                target_id,
                "❤️ Кто-то поставил вам лайк! Загляните в раздел «Смотреть анкеты», "
                "чтобы узнать, ответит ли симпатия взаимностью."
            )
        except Exception:
            pass

    await callback.answer()
    await send_next_profile(callback.message, viewer_id)


# ==================== ЖАЛОБЫ ====================

@router.callback_query(F.data.startswith("report:"))
async def on_report_start(callback: CallbackQuery, state: FSMContext):
    if db.is_banned(callback.from_user.id):
        await callback.answer("⛔️ Вы заблокированы.", show_alert=True)
        return
    target_id = int(callback.data.split(":")[1])
    await state.update_data(report_target=target_id)
    await state.set_state(ReportFlow.reason)
    await callback.answer()
    await callback.message.answer(
        "Опишите коротко причину жалобы (или отправьте «-», если без комментария):",
        reply_markup=kb.cancel_kb(),
    )


@router.message(ReportFlow.reason)
async def on_report_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    target_id = data["report_target"]
    reason = message.text.strip()
    db.add_report(message.from_user.id, target_id, reason)
    await state.clear()
    await message.answer(
        "🚩 Жалоба отправлена администратору. Спасибо!",
        reply_markup=kb.main_menu(is_admin(message.from_user.id)),
    )
    try:
        await message.bot.send_message(
            ADMIN_ID,
            f"🚩 Новая жалоба!\nНа пользователя ID {target_id}\n"
            f"От пользователя ID {message.from_user.id}\nПричина: {reason}"
        )
    except Exception:
        pass
    await send_next_profile(message, message.from_user.id)


@router.message(F.text == "❌ Отмена")
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.", reply_markup=kb.main_menu(is_admin(message.from_user.id)))


# ==================== АДМИН-ПАНЕЛЬ ====================

@router.message(F.text == "🛠 Админ-панель")
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Админ-панель:", reply_markup=kb.admin_menu_kb())


@router.message(Command("admin"))
async def admin_cmd(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Команда недоступна.")
        return
    await message.answer("Админ-панель:", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:stats")
async def adm_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    s = db.get_stats()
    text = (
        "📊 Статистика бота\n\n"
        f"👥 Всего пользователей: {s['total_users']}\n"
        f"🟢 Активных анкет: {s['active_profiles']}\n"
        f"⛔️ Заблокировано: {s['banned_users']}\n"
        f"❤️ Всего лайков: {s['total_likes']}\n"
        f"💑 Мэтчей: {s['total_matches']}\n"
        f"🚩 Открытых жалоб: {s['open_reports']}"
    )
    await callback.answer()
    await callback.message.answer(text, reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:list_users")
async def adm_list_users(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    users = db.list_recent_users(15)
    if not users:
        text = "Пользователей пока нет."
    else:
        lines = ["📋 Последние 15 пользователей:\n"]
        for u in users:
            status = "⛔️ бан" if u["is_banned"] else ("⏸ скрыта" if not u["is_active"] else "🟢")
            lines.append(f"ID {u['id']} — {u['name']}, {u['age']} лет — {status}")
        text = "\n".join(lines)
    await callback.answer()
    await callback.message.answer(text, reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:reports")
async def adm_reports(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    reports = db.get_open_reports(10)
    await callback.answer()
    if not reports:
        await callback.message.answer("Открытых жалоб нет.", reply_markup=kb.admin_menu_kb())
        return
    for r in reports:
        text = (
            f"🚩 Жалоба #{r['id']}\n"
            f"На пользователя ID: {r['reported_id']}\n"
            f"От пользователя ID: {r['reporter_id']}\n"
            f"Причина: {r['reason']}"
        )
        await callback.message.answer(
            text, reply_markup=kb.report_action_kb(r["id"], r["reported_id"])
        )


@router.callback_query(F.data.startswith("adm:ban_from_report:"))
async def adm_ban_from_report(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    _, _, report_id, reported_id = callback.data.split(":")
    db.set_banned(int(reported_id), True)
    db.resolve_report(int(report_id))
    await callback.answer("Пользователь забанен.")
    await callback.message.answer(f"🔨 Пользователь ID {reported_id} заблокирован. Жалоба закрыта.")


@router.callback_query(F.data.startswith("adm:dismiss_report:"))
async def adm_dismiss_report(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    report_id = int(callback.data.split(":")[2])
    db.resolve_report(report_id)
    await callback.answer("Жалоба отклонена.")
    await callback.message.answer(f"✅ Жалоба #{report_id} отклонена.")


@router.callback_query(F.data == "adm:ban")
async def adm_ban_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminFlow.wait_ban_id)
    await callback.answer()
    await callback.message.answer("Введите Telegram ID пользователя для блокировки:")


@router.message(AdminFlow.wait_ban_id)
async def adm_ban_apply(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID должен быть числом. Попробуйте ещё раз.")
        return
    db.set_banned(int(message.text), True)
    await state.clear()
    await message.answer(f"🔨 Пользователь {message.text} заблокирован.", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:unban")
async def adm_unban_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminFlow.wait_unban_id)
    await callback.answer()
    await callback.message.answer("Введите Telegram ID пользователя для разблокировки:")


@router.message(AdminFlow.wait_unban_id)
async def adm_unban_apply(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID должен быть числом. Попробуйте ещё раз.")
        return
    db.set_banned(int(message.text), False)
    await state.clear()
    await message.answer(f"✅ Пользователь {message.text} разблокирован.", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:disable")
async def adm_disable_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminFlow.wait_disable_id)
    await callback.answer()
    await callback.message.answer("Введите Telegram ID пользователя, чью анкету выключить:")


@router.message(AdminFlow.wait_disable_id)
async def adm_disable_apply(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID должен быть числом. Попробуйте ещё раз.")
        return
    db.set_active(int(message.text), False)
    await state.clear()
    await message.answer(f"⏸ Анкета пользователя {message.text} выключена.", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:enable")
async def adm_enable_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminFlow.wait_enable_id)
    await callback.answer()
    await callback.message.answer("Введите Telegram ID пользователя, чью анкету включить:")


@router.message(AdminFlow.wait_enable_id)
async def adm_enable_apply(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("ID должен быть числом. Попробуйте ещё раз.")
        return
    db.set_active(int(message.text), True)
    await state.clear()
    await message.answer(f"▶️ Анкета пользователя {message.text} включена.", reply_markup=kb.admin_menu_kb())


@router.callback_query(F.data == "adm:boost_self")
async def adm_boost_self(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    if not db.user_exists(callback.from_user.id):
        await callback.answer()
        await callback.message.answer("У вас нет анкеты — сначала создайте её через /start.")
        return
    until = db.boost_user(callback.from_user.id, BOOST_DURATION_HOURS)
    await callback.answer("Буст активирован!")
    await callback.message.answer(
        f"🚀 Ваша анкета будет показываться первой в очереди у всех пользователей "
        f"следующие {BOOST_DURATION_HOURS} ч. (до {until} UTC).",
        reply_markup=kb.admin_menu_kb(),
    )


@router.callback_query(F.data == "adm:fake_likes_self")
async def adm_fake_likes_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminFlow.wait_fake_likes_amount)
    await callback.answer()
    await callback.message.answer("Сколько лайков добавить к счётчику вашей анкеты? Введите число:")


@router.message(AdminFlow.wait_fake_likes_amount)
async def adm_fake_likes_apply(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите целое число.")
        return
    amount = int(message.text)
    db.add_fake_likes(message.from_user.id, amount)
    total = db.get_likes_count(message.from_user.id)
    await state.clear()
    await message.answer(
        f"❤️ Добавлено {amount} лайков. Теперь счётчик на вашей анкете показывает: {total}.\n"
        f"(Это только отображаемое число — реальных мэтчей это не создаёт.)",
        reply_markup=kb.admin_menu_kb(),
    )


@router.callback_query(F.data == "adm:broadcast")
async def adm_broadcast_ask(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer()
    await state.set_state(AdminFlow.wait_broadcast_content)
    await callback.answer()
    await callback.message.answer(
        "Пришлите сообщение для рассылки: текст, фото или видео с подписью.\n"
        "Форматирование, ссылки и премиум-эмодзи сохранятся как есть — сообщение "
        "будет разослано пользователям один в один.\n\n"
        "Для отмены нажмите «❌ Отмена»."
    )


@router.message(AdminFlow.wait_broadcast_content)
async def adm_broadcast_receive(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.update_data(
        broadcast_chat_id=message.chat.id,
        broadcast_message_id=message.message_id,
    )
    await state.set_state(AdminFlow.wait_broadcast_confirm)
    await message.answer("Так сообщение увидят пользователи 👇")
    await message.copy_to(message.chat.id)
    await message.answer(
        "Разослать это сообщение всем пользователям бота?",
        reply_markup=kb.broadcast_confirm_kb(),
    )


@router.message(AdminFlow.wait_broadcast_confirm, F.text == "✅ Разослать")
async def adm_broadcast_send(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    src_chat_id = data.get("broadcast_chat_id")
    src_message_id = data.get("broadcast_message_id")
    await state.clear()

    if not src_chat_id or not src_message_id:
        await message.answer("Не нашёл сообщение для рассылки, попробуйте заново.",
                              reply_markup=kb.admin_menu_kb())
        return

    await message.answer("⏳ Начинаю рассылку…", reply_markup=kb.main_menu(True))

    user_ids = db.get_all_user_ids()
    sent, failed = 0, 0
    for uid in user_ids:
        try:
            await message.bot.copy_message(
                chat_id=uid, from_chat_id=src_chat_id, message_id=src_message_id,
            )
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # не спамим Telegram API слишком быстро

    await message.answer(
        f"📢 Рассылка завершена.\n✅ Доставлено: {sent}\n⚠️ Не доставлено: {failed}",
        reply_markup=kb.admin_menu_kb(),
    )


# ==================== ЗАПУСК ====================

async def main():
    db.init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("Бот запущен")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
