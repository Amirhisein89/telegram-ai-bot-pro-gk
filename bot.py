# ============================
#          bot.py
# ============================

import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, BufferedInputFile,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, ADMIN_ID
from database import (
    init_db, upsert_user,
    is_subscribed, activate_subscription,
    subscription_info, add_code, delete_code,
    list_codes, list_users
)
from ai_handler import ask_ai, generate_image

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


user_mode: dict[int, str] = {}

chat_history: dict[int, list] = {}


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 شروع چت با AiAR89")],
            [KeyboardButton(text="🧠 چت طولانی"), KeyboardButton(text="✉️ پیام کوتاه")],
            [KeyboardButton(text="🔑 فعال‌سازی اشتراک"), KeyboardButton(text="📊 وضعیت اشتراک")],
            [KeyboardButton(text="ℹ️ راهنما")],
        ],
        resize_keyboard=True,
        input_field_placeholder="یه گزینه انتخاب کن..."
    )


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤖 شروع چت با AiAR89")],
            [KeyboardButton(text="🧠 چت طولانی"), KeyboardButton(text="✉️ پیام کوتاه")],
            [KeyboardButton(text="🔑 فعال‌سازی اشتراک"), KeyboardButton(text="📊 وضعیت اشتراک")],
            [KeyboardButton(text="➕ افزودن کد"), KeyboardButton(text="📋 لیست کدها")],
            [KeyboardButton(text="👥 لیست کاربران"), KeyboardButton(text="ℹ️ راهنما")],
        ],
        resize_keyboard=True,
        input_field_placeholder="یه گزینه انتخاب کن..."
    )


def chat_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔴 پایان چت")],
        ],
        resize_keyboard=True,
        input_field_placeholder="پیامت رو بنویس یا تصویر: ... برای ساخت عکس"
    )


def get_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    if user_id == ADMIN_ID:
        return admin_keyboard()
    return main_menu_keyboard()



def user_tag(msg: Message) -> str:
    name = msg.from_user.full_name or "بدون نام"
    uid = msg.from_user.id
    username = f"@{msg.from_user.username}" if msg.from_user.username else "بدون یوزرنیم"
    return f"👤 <b>{name}</b> | {username} | <code>{uid}</code>"


async def notify_admin(text: str):
    try:
        await bot.send_message(ADMIN_ID, text)
    except Exception as e:
        logging.error(f"خطا در ارسال به ادمین: {e}")


def clear_user_session(user_id: int):
    user_mode.pop(user_id, None)
    chat_history.pop(user_id, None)


@dp.message(CommandStart())
async def cmd_start(msg: Message):
    user = msg.from_user
    await upsert_user(user.id, user.username or "", user.full_name or "")
    clear_user_session(user.id)

    await notify_admin(
        f"🟢 <b>کاربر استارت زد!</b>\n"
        f"{user_tag(msg)}"
    )

    await msg.answer(
        f"سلام <b>{user.first_name}</b>! 👋\n\n"
        f"به <b>AiAR89</b> خوش اومدی!\n"
        f"یه هوش مصنوعی قدرتمند که میتونه سوالاتت رو جواب بده و تصویر بسازه.\n\n"
        f"از منوی پایین شروع کن 👇",
        reply_markup=get_keyboard(user.id)
    )



@dp.message(F.text == "🤖 شروع چت با AiAR89")
async def btn_start_chat(msg: Message):
    user = msg.from_user
    await upsert_user(user.id, user.username or "", user.full_name or "")

    if not await is_subscribed(user.id):
        await msg.answer(
            "⚠️ <b>اشتراک فعال نداری!</b>\n\n"
            "روی <b>فعال‌سازی اشتراک</b> بزن.",
            reply_markup=get_keyboard(user.id)
        )
        return

    user_mode[user.id] = "long"
    chat_history[user.id] = []
    _, days_left = await subscription_info(user.id)

    await msg.answer(
        f"✅ <b>چت با AiAR89 شروع شد!</b>\n\n"
        f"⏳ {days_left} روز اشتراک باقیمانده\n\n"
        f"💬 هر سوالی داری بپرس\n"
        f"🖼 برای ساخت تصویر بنویس: <code>تصویر: توضیح</code>\n\n"
        f"برای پایان چت دکمه 🔴 رو بزن.",
        reply_markup=chat_keyboard()
    )



@dp.message(F.text == "🧠 چت طولانی")
async def btn_long_chat(msg: Message):
    user = msg.from_user
    await upsert_user(user.id, user.username or "", user.full_name or "")

    if not await is_subscribed(user.id):
        await msg.answer(
            "⚠️ <b>اشتراک فعال نداری!</b>\n\n"
            "روی <b>فعال‌سازی اشتراک</b> بزن.",
            reply_markup=get_keyboard(user.id)
        )
        return

    user_mode[user.id] = "long"
    chat_history[user.id] = []
    _, days_left = await subscription_info(user.id)

    await msg.answer(
        f"🧠 <b>چت طولانی شروع شد!</b>\n\n"
        f"در این حالت من همه چیزی که میگی رو <b>یادم میمونه</b>.\n"
        f"مثلاً اگه بگی اسمم علیه، بعداً هم یادمه! 😊\n\n"
        f"⏳ {days_left} روز اشتراک باقیمانده\n\n"
        f"برای پایان چت دکمه 🔴 رو بزن.",
        reply_markup=chat_keyboard()
    )


@dp.message(F.text == "✉️ پیام کوتاه")
async def btn_short_chat(msg: Message):
    user = msg.from_user
    await upsert_user(user.id, user.username or "", user.full_name or "")

    if not await is_subscribed(user.id):
        await msg.answer(
            "⚠️ <b>اشتراک فعال نداری!</b>\n\n"
            "روی <b>فعال‌سازی اشتراک</b> بزن.",
            reply_markup=get_keyboard(user.id)
        )
        return

    user_mode[user.id] = "short"
    _, days_left = await subscription_info(user.id)

    await msg.answer(
        f"✉️ <b>پیام کوتاه شروع شد!</b>\n\n"
        f"در این حالت هر پیام <b>مستقل</b> هست.\n"
        f"بات هیچ چیزی از پیام‌های قبلی یادش نیست.\n\n"
        f"⏳ {days_left} روز اشتراک باقیمانده\n\n"
        f"برای پایان چت دکمه 🔴 رو بزن.",
        reply_markup=chat_keyboard()
    )


@dp.message(F.text == "🔴 پایان چت")
async def btn_end_chat(msg: Message):
    clear_user_session(msg.from_user.id)
    await msg.answer(
        "👋 چت پایان یافت.\n\n"
        "از منوی زیر میتونی دوباره شروع کنی.",
        reply_markup=get_keyboard(msg.from_user.id)
    )



@dp.message(F.text == "📊 وضعیت اشتراک")
async def btn_status(msg: Message):
    subscribed = await is_subscribed(msg.from_user.id)
    if subscribed:
        expires, days_left = await subscription_info(msg.from_user.id)
        await msg.answer(
            f"✅ <b>اشتراک فعال</b>\n"
            f"📅 انقضا: <code>{expires.strftime('%Y-%m-%d')}</code>\n"
            f"⏳ {days_left} روز باقیمانده",
            reply_markup=get_keyboard(msg.from_user.id)
        )
    else:
        await msg.answer(
            "❌ <b>اشتراک فعال نیست</b>\n\n"
            "روی <b>فعال‌سازی اشتراک</b> بزن.",
            reply_markup=get_keyboard(msg.from_user.id)
        )


@dp.message(F.text == "🔑 فعال‌سازی اشتراک")
async def btn_activate_prompt(msg: Message):
    await msg.answer(
        "🔑 کد اشتراکت رو به این شکل وارد کن:\n\n"
        "<code>/activate کد_اشتراک</code>\n\n"
        "مثال: <code>/activate AIAR89-VIP1</code>"
    )


@dp.message(F.text == "ℹ️ راهنما")
async def btn_help(msg: Message):
    await msg.answer(
        "<b>📖 راهنمای AiAR89</b>\n\n"
        "🤖 <b>شروع چت</b> — چت معمولی با هوش مصنوعی\n"
        "🧠 <b>چت طولانی</b> — بات همه چیز رو توی مکالمه یادش میمونه\n"
        "✉️ <b>پیام کوتاه</b> — هر پیام مستقل، بدون حافظه\n"
        "🔑 <b>فعال‌سازی اشتراک</b> — وارد کردن کد اشتراک\n"
        "📊 <b>وضعیت اشتراک</b> — نمایش روزهای باقیمانده\n\n"
        "🖼 <b>ساخت تصویر:</b>\n"
        "داخل چت بنویس: <code>تصویر: توضیح</code>\n\n"
        "👨‍💻 <b>سازنده:</b> امیرحسین رشیدی راد",
        reply_markup=get_keyboard(msg.from_user.id)
    )


@dp.message(F.text == "➕ افزودن کد", F.from_user.id == ADMIN_ID)
async def btn_addcode_prompt(msg: Message):
    await msg.answer(
        "➕ کد جدید رو به این شکل وارد کن:\n\n"
        "<code>/addcode کد</code>\n\n"
        "مثال: <code>/addcode AIAR89-VIP1</code>"
    )


@dp.message(F.text == "📋 لیست کدها", F.from_user.id == ADMIN_ID)
async def btn_list_codes(msg: Message):
    codes = await list_codes()
    if not codes:
        await msg.answer("📭 هیچ کدی ثبت نشده.")
        return
    lines = ["<b>📋 لیست کدهای اشتراک:</b>\n"]
    for c in codes:
        status = "✅ آزاد" if not c["used"] else f"🔴 استفاده‌شده (کاربر: <code>{c['used_by']}</code>)"
        lines.append(f"• <code>{c['code']}</code> — {status}")
    await msg.answer("\n".join(lines))


@dp.message(F.text == "👥 لیست کاربران", F.from_user.id == ADMIN_ID)
async def btn_list_users(msg: Message):
    users = await list_users()
    if not users:
        await msg.answer("📭 هیچ کاربری ثبت نشده.")
        return
    lines = [f"<b>👥 تعداد کاربران: {len(users)}</b>\n"]
    for u in users:
        sub = "✅ فعال" if u["sub_expires"] else "❌ ندارد"
        name = u["first_name"] or "بدون نام"
        lines.append(f"• <b>{name}</b> | <code>{u['user_id']}</code> | اشتراک: {sub}")
    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n... و بیشتر"
    await msg.answer(text)



@dp.message(Command("activate"))
async def cmd_activate(msg: Message):
    parts = msg.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("❌ مثال: <code>/activate ABC123</code>")
        return

    code = parts[1].strip()
    user = msg.from_user

    if await is_subscribed(user.id):
        _, days_left = await subscription_info(user.id)
        await msg.answer(f"⚠️ اشتراک تو هنوز فعاله ({days_left} روز باقیمانده)!")
        return

    success = await activate_subscription(user.id, code)
    if success:
        expires, _ = await subscription_info(user.id)
        await msg.answer(
            f"🎉 <b>اشتراک با موفقیت فعال شد!</b>\n\n"
            f"✅ کد: <code>{code}</code>\n"
            f"📅 انقضا: <code>{expires.strftime('%Y-%m-%d')}</code>\n\n"
            f"حالا از منو یه حالت چت انتخاب کن!",
            reply_markup=get_keyboard(user.id)
        )
        await notify_admin(
            f"🔑 <b>کد اشتراک استفاده شد</b>\n"
            f"{user_tag(msg)}\n"
            f"کد: <code>{code}</code>"
        )
    else:
        await msg.answer(
            f"❌ کد <code>{code}</code> نامعتبر یا قبلاً استفاده شده!\n"
            f"با ادمین تماس بگیر."
        )


@dp.message(Command("addcode"), F.from_user.id == ADMIN_ID)
async def cmd_addcode(msg: Message):
    parts = msg.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("❌ مثال: <code>/addcode ABC123</code>")
        return
    code = parts[1].strip()
    success = await add_code(code)
    if success:
        await msg.answer(f"✅ کد <code>{code}</code> اضافه شد.")
    else:
        await msg.answer(f"⚠️ کد <code>{code}</code> قبلاً وجود داره!")


@dp.message(Command("delcode"), F.from_user.id == ADMIN_ID)
async def cmd_delcode(msg: Message):
    parts = msg.text.strip().split(maxsplit=1)
    if len(parts) < 2:
        await msg.answer("❌ مثال: <code>/delcode ABC123</code>")
        return
    code = parts[1].strip()
    success = await delete_code(code)
    if success:
        await msg.answer(f"✅ کد <code>{code}</code> حذف شد.")
    else:
        await msg.answer(f"❌ کد <code>{code}</code> پیدا نشد!")


@dp.message(F.photo)
async def handle_photo(msg: Message):
    user = msg.from_user
    await upsert_user(user.id, user.username or "", user.full_name or "")

    await notify_admin(
        f"🖼 <b>کاربر عکس فرستاد:</b>\n"
        f"{user_tag(msg)}\n"
        f"کپشن: {msg.caption or '—'}"
    )
    try:
        await bot.forward_message(ADMIN_ID, msg.chat.id, msg.message_id)
    except Exception:
        pass

    if not await is_subscribed(user.id):
        await msg.answer("⚠️ اشتراک فعال نداری!", reply_markup=get_keyboard(user.id))
        return

    await msg.answer("🖼 عکست رو دیدم! اگه سوالی داری بنویس.")



@dp.message(F.text)
async def handle_text(msg: Message):
    user = msg.from_user
    text = msg.text.strip()

    skip_notify = any(text.startswith(x) for x in [
        "/", "🤖", "🔴", "🧠", "✉️", "🔑", "📊", "ℹ️", "➕", "📋", "👥"
    ])
    if not skip_notify:
        await notify_admin(
            f"💬 <b>پیام جدید:</b>\n"
            f"{user_tag(msg)}\n"
            f"📝 {text}"
        )

    await upsert_user(user.id, user.username or "", user.full_name or "")

    mode = user_mode.get(user.id)

    if not mode:
        await msg.answer(
            "برای شروع یه حالت چت انتخاب کن 👇",
            reply_markup=get_keyboard(user.id)
        )
        return

    if not await is_subscribed(user.id):
        clear_user_session(user.id)
        await msg.answer(
            "⚠️ اشتراک تو منقضی شده!\n"
            "برای تمدید با ادمین تماس بگیر.",
            reply_markup=get_keyboard(user.id)
        )
        return


    if text.startswith("تصویر:") or text.startswith("تصویر :"):
        prompt = text.split(":", 1)[1].strip()
        if not prompt:
            await msg.answer(
                "❌ توضیح تصویر رو بنویس!\n"
                "مثال: <code>تصویر: غروب آفتاب کنار دریا</code>"
            )
            return

        wait_msg = await msg.answer("🎨 در حال ساخت تصویر... لطفاً صبر کن ⏳")
        image_bytes = await generate_image(prompt)
        try:
            await wait_msg.delete()
        except Exception:
            pass

        if image_bytes:
            await msg.answer_photo(
                photo=BufferedInputFile(image_bytes, filename="image.jpg"),
                caption=f"🖼 تصویر برای: <i>{prompt}</i>"
            )
        else:
            await msg.answer(
                "❌ ساخت تصویر با خطا مواجه شد.\n"
                "دوباره تلاش کن یا توضیح رو به انگلیسی بنویس."
            )
        return

    if mode == "short":
        wait_msg = await msg.answer("🤔 در حال پردازش...")
        answer = await ask_ai(prompt=text)
        try:
            await wait_msg.delete()
        except Exception:
            pass


    elif mode == "long":
        history = chat_history.setdefault(user.id, [])
        history.append({"role": "user", "content": text})

        wait_msg = await msg.answer("🤔 در حال پردازش...")
        answer = await ask_ai(prompt=text, history=history)
        try:
            await wait_msg.delete()
        except Exception:
            pass

        history.append({"role": "assistant", "content": answer})

        if len(history) > 20:
            chat_history[user.id] = history[-20:]
    else:
        return

    if len(answer) > 4000:
        for chunk in [answer[i:i+4000] for i in range(0, len(answer), 4000)]:
            await msg.answer(chunk)
    else:
        await msg.answer(answer)



async def main():
    await init_db()
    logging.info("✅ بات شروع به کار کرد!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
