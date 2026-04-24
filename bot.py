import os
import asyncio
import json
import random

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from db import *

TOKEN = os.getenv("8600741649:AAFJyvAlARo8BkfbyqysHDnNFxyCDRT42wU")

if not TOKEN:
    raise Exception("BOT_TOKEN not set")

bot = Bot(token=TOKEN)
dp = Dispatcher()

with open("vocab.json", "r", encoding="utf-8") as f:
    vocab = json.load(f)

user_data = {}

# ---------- KEYBOARDS ----------

def kb(btns):
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

lang_kb = kb([
    [KeyboardButton(text="Russian 🇷🇺")],
    [KeyboardButton(text="Uzbek 🇺🇿")]
])

main_kb = kb([
    [KeyboardButton(text="📚 Learning Mode")],
    [KeyboardButton(text="📝 Exam Mode")],
    [KeyboardButton(text="🏆 Leaderboard")]
])

direction_kb = kb([
    [KeyboardButton(text="EN → Native")],
    [KeyboardButton(text="Native → EN")]
])

end_kb = kb([
    [KeyboardButton(text="🏆 Leaderboard")],
    [KeyboardButton(text="🔙 Main Menu")]
])

# ---------- START ----------

@dp.message(Command("start"))
async def start(message: types.Message):
    user_data[message.from_user.id] = {"step": "name"}

    await message.answer(
        "Welcome! 👋\n\n"
        "Enter:\nName Surname Group\n\n"
        "Example:\nAsadbek Rakhmatov 101"
    )

# ---------- MAIN HANDLER ----------

@dp.message()
async def handle(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    user = user_data.setdefault(user_id, {})

    # -------- STEP 1: NAME --------
    if user.get("step") == "name":
        parts = text.split()

        if len(parts) < 3:
            await message.answer("Please enter: Name Surname Group")
            return

        name = " ".join(parts[:-1])
        group = parts[-1]

        user["name"] = name
        user["group"] = group

        add_user(user_id, name)

        user["step"] = "language"

        await message.answer("Choose language:", reply_markup=lang_kb)
        return

    # -------- STEP 2: LANGUAGE --------
    if text == "Russian 🇷🇺":
        user["lang"] = "ru"
        user["step"] = "menu"
        await message.answer("Choose mode:", reply_markup=main_kb)
        return

    if text == "Uzbek 🇺🇿":
        user["lang"] = "uz"
        user["step"] = "menu"
        await message.answer("Choose mode:", reply_markup=main_kb)
        return

    # -------- MAIN MENU --------
    if text == "🔙 Main Menu":
        await message.answer("Choose mode:", reply_markup=main_kb)
        return

    # -------- LEARNING MODE --------
    if text == "📚 Learning Mode":
        user["study_mode"] = "learning"
        await message.answer("Choose direction:", reply_markup=direction_kb)
        return

    if text == "EN → Native":
        user["mode"] = "en_to_native"
        await start_test(message, user)
        return

    if text == "Native → EN":
        user["mode"] = "native_to_en"
        await start_test(message, user)
        return

    # -------- EXAM MODE --------
    if text == "📝 Exam Mode":
        user["study_mode"] = "exam"
        user["mode"] = "mixed"
        await start_test(message, user)
        return

    # -------- LEADERBOARD --------
    if text == "🏆 Leaderboard":
        top = get_leaderboard()

        text_out = "🏆 Leaderboard:\n\n"
        for i, (name, score) in enumerate(top, 1):
            text_out += f"{i}. {name} — {score}\n"

        await message.answer(text_out, reply_markup=end_kb)
        return

    # -------- ANSWER --------
    if "current" in user and text in user["current"]["options"]:
        await process_answer(message, user, text)
        return


# ---------- TEST LOGIC ----------

async def start_test(message, user):
    words = vocab["Elementary"]["1A"]

    user.update({
        "all_words": words.copy(),
        "queue": random.sample(words, len(words)),
        "mistakes": [],
        "score": 0,
        "correct": 0
    })

    await ask(message, user)


async def ask(message, user):
    if not user["queue"]:
        total = len(user["all_words"])

        cursor.execute("""
        INSERT INTO history (user_id, unit, score, total)
        VALUES (%s, %s, %s, %s)
        """, (message.from_user.id, "1ABC", user["score"], total))
        conn.commit()

        await message.answer(
            f"Finished!\n\nScore: {user['score']} / {total}",
            reply_markup=end_kb
        )
        return

    word = user["queue"].pop()

    # -------- MIXED MODE --------
    if user["mode"] == "mixed":
        if random.choice([True, False]):
            q = word["en"]
            correct = word[user["lang"]]
            key = user["lang"]
        else:
            q = word[user["lang"]]
            correct = word["en"]
            key = "en"

    # -------- NORMAL MODES --------
    elif user["mode"] == "en_to_native":
        q = word["en"]
        correct = word[user["lang"]]
        key = user["lang"]

    else:
        q = word[user["lang"]]
        correct = word["en"]
        key = "en"

    options = [correct]

    while len(options) < 3:
        w = random.choice(user["all_words"])[key]
        if w not in options:
            options.append(w)

    random.shuffle(options)

    user["current"] = {
        "word": word,
        "correct": correct,
        "options": options,
        "attempts": 0
    }

    buttons = [[KeyboardButton(text=o)] for o in options]

    await message.answer(q, reply_markup=kb(buttons))


# ---------- ANSWER PROCESS ----------

async def process_answer(message, user, text):
    q = user["current"]
    q["attempts"] += 1

    correct = q["correct"]

    # -------- CORRECT --------
    if text == correct:

        if user["study_mode"] == "learning":
            if q["attempts"] == 1:
                user["score"] += 1
            elif q["attempts"] == 2:
                user["score"] += 0.5
        else:
            user["score"] += 1

        user["correct"] += 1
        await ask(message, user)

    # -------- WRONG --------
    else:
        if user["study_mode"] == "learning" and q["attempts"] < 2:
            await message.answer("Try again")
            return

        user["mistakes"].append(q["word"])
        await ask(message, user)


# ---------- RUN ----------

async def main():
    init_db()
    print("Bot running...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())