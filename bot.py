import asyncio
import random
import time
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import config
from database import (
    init_db, get_user, update_balance, update_field,
    add_item, remove_item, get_inventory, get_top
)

bot = Bot(token=config.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# ==================== СТАРТ ====================
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user = await get_user(message.from_user.id, message.from_user.username)
    text = (
        f"👋 Привет, <b>{message.from_user.first_name}</b>!\n\n"
        f"💼 Баланс: <b>{user['balance']} {config.CURRENCY}</b>\n\n"
        f"📋 <b>Команды:</b>\n"
        f"/balance — баланс\n"
        f"/work — работа\n"
        f"/daily — ежедневный бонус\n"
        f"/shop — магазин 🏪\n"
        f"/inventory — инвентарь\n"
        f"/mybusiness — мои бизнесы\n"
        f"/casino [ставка] — казино\n"
        f"/top — топ игроков\n"
        f"/profile — профиль"
    )
    await message.answer(text)


# ==================== БАЛАНС ====================
@dp.message(Command("balance"))
async def cmd_balance(message: Message):
    user = await get_user(message.from_user.id, message.from_user.username)
    await message.answer(
        f"💼 Баланс: <b>{user['balance']} {config.CURRENCY}</b>\n"
        f"📈 Всего заработано: {user['total_earned']} {config.CURRENCY}"
    )


# ==================== РАБОТА ====================
@dp.message(Command("work"))
async def cmd_work(message: Message):
    user = await get_user(message.from_user.id, message.from_user.username)
    now = int(time.time())
    last = user["last_work"]

    if now - last < config.WORK_COOLDOWN:
        wait = config.WORK_COOLDOWN - (now - last)
        await message.answer(f"⏳ Отдохни! Следующая работа через <b>{wait} сек.</b>")
        return

    earnings = random.randint(config.WORK_MIN, config.WORK_MAX)
    jobs = ["программистом", "курьером", "баристой", "таксистом", "грузчиком", "дизайнером"]
    job = random.choice(jobs)

    await update_balance(message.from_user.id, earnings)
    await update_field(message.from_user.id, "last_work", now)
    await message.answer(
        f"💼 Ты поработал {job} и заработал <b>{earnings} {config.CURRENCY}</b>!"
    )


# ==================== DAILY ====================
@dp.message(Command("daily"))
async def cmd_daily(message: Message):
    user = await get_user(message.from_user.id, message.from_user.username)
    now = int(time.time())
    last = user["last_daily"]

    if now - last < config.DAILY_COOLDOWN:
        wait = config.DAILY_COOLDOWN - (now - last)
        hours = wait // 3600
        minutes = (wait % 3600) // 60
        await message.answer(f"⏳ Бонус будет доступен через <b>{hours}ч {minutes}м</b>")
        return

    await update_balance(message.from_user.id, config.DAILY_REWARD)
    await update_field(message.from_user.id, "last_daily", now)
    await message.answer(f"🎁 Ты получил ежедневный бонус: <b>{config.DAILY_REWARD} {config.CURRENCY}</b>!")


# ==================== 🏪 МАГАЗИН — МЕНЮ ====================
def shop_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Бизнесы", callback_data="shop_cat_business")],
        [InlineKeyboardButton(text="🎒 Предметы", callback_data="shop_cat_items")],
        [InlineKeyboardButton(text="🎰 Развлечения", callback_data="shop_cat_fun")],
    ])


@dp.message(Command("shop"))
async def cmd_shop(message: Message):
    await message.answer("🏪 <b>Магазин</b>\n\nВыбери раздел:", reply_markup=shop_menu_kb())


@dp.callback_query(F.data == "shop_menu")
async def cb_shop_menu(call: CallbackQuery):
    await call.message.edit_text("🏪 <b>Магазин</b>\n\nВыбери раздел:", reply_markup=shop_menu_kb())
    await call.answer()


@dp.callback_query(F.data == "shop_cat_business")
async def cb_shop_business(call: CallbackQuery):
    text = "💼 <b>БИЗНЕСЫ</b>\n\n"
    for name, info in config.BUSINESSES.items():
        text += (
            f"{name}\n"
            f"💰 Цена: <b>{info['price']}</b> {config.CURRENCY}\n"
            f"📈 Доход: <b>{info['income']}</b> {config.CURRENCY}/час\n"
            f"<i>{info['description']}</i>\n\n"
        )
    text += "💡 Купить: <code>/buy Название</code>\n📋 Свои бизнесы: /mybusiness"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data == "shop_cat_items")
async def cb_shop_items(call: CallbackQuery):
    text = "🎒 <b>ПРЕДМЕТЫ</b>\n\n"
    for name, info in config.ITEMS.items():
        text += f"{name} — <b>{info['price']}</b> {config.CURRENCY}\n<i>{info['description']}</i>\n\n"
    text += "💡 Купить: <code>/buy Название</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


@dp.callback_query(F.data == "shop_cat_fun")
async def cb_shop_fun(call: CallbackQuery):
    text = "🎰 <b>РАЗВЛЕЧЕНИЯ</b>\n\n"
    for name, info in config.FUN.items():
        text += f"{name} — <b>{info['price']}</b> {config.CURRENCY}\n<i>{info['description']}</i>\n\n"
    text += "💡 Купить: <code>/buy Название</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="shop_menu")]])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()


# ==================== ПОКУПКА ====================
@dp.message(Command("buy"))
async def cmd_buy(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Использование: <code>/buy Название</code>")
        return

    item_query = args[1].strip().lower()
    all_items = {}
    all_items.update(config.BUSINESSES)
    all_items.update(config.ITEMS)
    all_items.update(config.FUN)

    matched = None
    for name in all_items:
        if item_query in name.lower():
            matched = name
            break

    if not matched:
        await message.answer("❌ Такого товара нет. Смотри /shop")
        return

    item = all_items[matched]
    user = await get_user(message.from_user.id, message.from_user.username)

    if user["balance"] < item["price"]:
        await message.answer(
            f"❌ Недостаточно средств!\nНужно: <b>{item['price']} {config.CURRENCY}</b>\n"
            f"У тебя: <b>{user['balance']} {config.CURRENCY}</b>"
        )
        return

    await update_balance(message.from_user.id, -item["price"])
    await add_item(message.from_user.id, matched)

    if matched in config.BUSINESSES:
        await message.answer(
            f"🎉 Ты купил бизнес: <b>{matched}</b>!\n"
            f"📈 Теперь он приносит <b>{item['income']} {config.CURRENCY}/час</b>!\n"
            f"Проверить: /mybusiness"
        )
    else:
        await message.answer(f"✅ Ты купил <b>{matched}</b> за <b>{item['price']} {config.CURRENCY}</b>!")


# ==================== МОИ БИЗНЕСЫ ====================
@dp.message(Command("mybusiness"))
async def cmd_mybusiness(message: Message):
    items = await get_inventory(message.from_user.id)
    businesses = [i for i in items if i["item_name"] in config.BUSINESSES]

    if not businesses:
        await message.answer("💼 У тебя пока нет бизнесов.\nЗагляни в /shop → 💼 Бизнесы")
        return

    total_income = 0
    text = "💼 <b>Мои бизнесы:</b>\n\n"
    for b in businesses:
        info = config.BUSINESSES[b["item_name"]]
        income = info["income"] * b["quantity"]
        total_income += income
        text += f"{b['item_name']} × <b>{b['quantity']}</b> → <b>{income} {config.CURRENCY}/час</b>\n"

    text += f"\n💰 <b>Общий доход: {total_income} {config.CURRENCY}/час</b>\n\n💡 Доход начисляется автоматически раз в час."
    await message.answer(text)


# ==================== ИНВЕНТАРЬ ====================
@dp.message(Command("inventory"))
async def cmd_inventory(message: Message):
    items = await get_inventory(message.from_user.id)
    if not items:
        await message.answer("🎒 Инвентарь пуст. Загляни в /shop!")
        return

    text = "🎒 <b>Твой инвентарь:</b>\n\n"
    for item in items:
        text += f"• {item['item_name']} × <b>{item['quantity']}</b>\n"
    await message.answer(text)


# ==================== КАЗИНО ====================
@dp.message(Command("casino"))
async def cmd_casino(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(f"❌ Использование: <code>/casino [ставка]</code>\nМин: {config.CASINO_MIN_BET}, Макс: {config.CASINO_MAX_BET}")
        return

    bet = int(args[1])
    if bet < config.CASINO_MIN_BET or bet > config.CASINO_MAX_BET:
        await message.answer(f"❌ Ставка от {config.CASINO_MIN_BET} до {config.CASINO_MAX_BET}")
        return

    user = await get_user(message.from_user.id, message.from_user.username)
    if user["balance"] < bet:
        await message.answer("❌ Недостаточно средств!")
        return

    if random.random() < config.CASINO_WIN_CHANCE:
        win = bet * config.CASINO_WIN_MULTIPLIER
        await update_balance(message.from_user.id, win - bet)
        await message.answer(f"🎰 🎉 <b>ПОБЕДА!</b>\nТы выиграл <b>{win} {config.CURRENCY}</b>!")
    else:
        await update_balance(message.from_user.id, -bet)
        await message.answer(f"🎰 😢 <b>Проигрыш...</b>\nТы потерял {bet} {config.CURRENCY}")


# ==================== ТОП ====================
@dp.message(Command("top"))
async def cmd_top(message: Message):
    top = await get_top(10)
    if not top:
        await message.answer("Пока никого нет 😴")
        return

    medals = ["🥇", "🥈", "🥉"]
    text = "🏆 <b>Топ игроков:</b>\n\n"
    for i, u in enumerate(top):
        prefix = medals[i] if i < 3 else f"{i+1}."
        text += f"{prefix} {u['username']} — <b>{u['balance']} {config.CURRENCY}</b>\n"
    await message.answer(text)


# ==================== ПРОФИЛЬ ====================
@dp.message(Command("profile"))
async def cmd_profile(message: Message):
    user = await get_user(message.from_user.id, message.from_user.username)
    items = await get_inventory(message.from_user.id)

    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"🆔 ID: <code>{user['user_id']}</code>\n"
        f"📛 Имя: {user['username']}\n"
        f"💰 Баланс: <b>{user['balance']} {config.CURRENCY}</b>\n"
        f"📈 Заработано: {user['total_earned']} {config.CURRENCY}\n"
        f"🎒 Предметов: {sum(i['quantity'] for i in items)}"
    )
    await message.answer(text)


# ==================== АВТО-ДОХОД С БИЗНЕСОВ ====================
async def business_income_loop():
    while True:
        await asyncio.sleep(config.BUSINESS_INCOME_INTERVAL)
        try:
            import aiosqlite
            async with aiosqlite.connect("game.db") as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT user_id FROM users") as cursor:
                    users = await cursor.fetchall()

                for u in users:
                    uid = u["user_id"]
                    items = await get_inventory(uid)
                    total = 0
                    for item in items:
                        if item["item_name"] in config.BUSINESSES:
                            total += config.BUSINESSES[item["item_name"]]["income"] * item["quantity"]
                    if total > 0:
                        await update_balance(uid, total)
                        try:
                            await bot.send_message(uid, f"💼 <b>Доход с бизнесов!</b>\nТы получил <b>{total} {config.CURRENCY}</b>!")
                        except Exception:
                            pass
        except Exception as e:
            print(f"Ошибка в business_income_loop: {e}")


# ==================== ЗАПУСК ====================
async def main():
    await init_db()
    asyncio.create_task(business_income_loop())
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())