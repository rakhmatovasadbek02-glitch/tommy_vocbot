import os, asyncio, json, random
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

from db import *

TOKEN = os.getenv("8600741649:AAFJyvAlARo8BkfbyqysHDnNFxyCDRT42wU")

EDITOR_ID = 111111111
TEACHER_ID = 222222222

bot = Bot(token=TOKEN)
dp = Dispatcher()

with open("vocab.json", "r", encoding="utf-8") as f:
    vocab = json.load(f)

user_data = {}

def kb(btns):
    return ReplyKeyboardMarkup(keyboard=btns, resize_keyboard=True)

lang_kb = kb([[KeyboardButton(text="Russian 🇷🇺")],
              [KeyboardButton(text="Uzbek 🇺🇿")]])

mode_kb = kb([[KeyboardButton(text="EN → Native")],
              [KeyboardButton(text="Native → EN")]])

study_kb = kb([[KeyboardButton(text="📚 Learning Mode")],
               [KeyboardButton(text="📝 Exam Mode")]])

main_student = kb([[KeyboardButton(text="📚 Start Learning")],
                   [KeyboardButton(text="📊 My Stats")]])

teacher_kb = kb([[KeyboardButton(text="👥 All Students")],
                 [KeyboardButton(text="🏆 Leaderboard")]])

editor_kb = kb([[KeyboardButton(text="📚 Start Learning")],
                [KeyboardButton(text="👥 All Students")],
                [KeyboardButton(text="🏆 Leaderboard")]])

@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name

    add_user(user_id, username)

    if user_id == EDITOR_ID:
        set_role(user_id, "editor")
    elif user_id == TEACHER_ID:
        set_role(user_id, "teacher")

    role = get_role(user_id)

    if role == "editor":
        await message.answer("Editor panel", reply_markup=editor_kb)
    elif role == "teacher":
        await message.answer("Teacher panel", reply_markup=teacher_kb)
    else:
        await message.answer("Student panel", reply_markup=main_student)

@dp.message(lambda m: m.text == "📚 Start Learning")
async def start_learning(message: types.Message):
    user_data[message.from_user.id] = {}
    await message.answer("Choose language:", reply_markup=lang_kb)

@dp.message()
async def handle(message: types.Message):
    user = user_data.setdefault(message.from_user.id, {})
    text = message.text

    if text == "Russian 🇷🇺":
        user["lang"] = "ru"
        await message.answer("Choose direction:", reply_markup=mode_kb)
        return

    if text == "Uzbek 🇺🇿":
        user["lang"] = "uz"
        await message.answer("Choose direction:", reply_markup=mode_kb)
        return

    if text == "EN → Native":
        user["mode"] = "en_to_native"
        await message.answer("Choose study mode:", reply_markup=study_kb)
        return

    if text == "Native → EN":
        user["mode"] = "native_to_en"
        await message.answer("Choose study mode:", reply_markup=study_kb)
        return

    if text == "📚 Learning Mode":
        user["study_mode"] = "learning"
        await start_test(message, user)
        return

    if text == "📝 Exam Mode":
        user["study_mode"] = "exam"
        await start_test(message, user)
        return

    if "current" in user and text in user["current"]["options"]:
        await process_answer(message, user, text)
        return

async def start_test(message, user):
    words = vocab["Elementary"]["1A"]

    user.update({
        "all_words": words.copy(),
        "queue": random.sample(words, len(words)),
        "mistakes": [],
        "score": 0,
        "correct": 0,
        "current_unit": "1ABC"
    })

    await ask(message, user)

async def ask(message, user):
    if not user["queue"]:
        if user["mistakes"] and user["study_mode"] == "learning":
            user["queue"] = user["mistakes"]
            user["mistakes"] = []
            await message.answer("🔁 Repeating mistakes...")
        else:
            total = len(user["all_words"])

            cursor.execute("""
            INSERT INTO history (user_id, unit, score, total)
            VALUES (%s, %s, %s, %s)
            """, (message.from_user.id, user["current_unit"], user["score"], total))
            conn.commit()

            await message.answer(f"Finished!\nScore: {user['score']}/{total}")
            return

    word = user["queue"].pop()

    if user["mode"] == "en_to_native":
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

    kb_buttons = [[KeyboardButton(text=o)] for o in options]
    await message.answer(q, reply_markup=kb(kb_buttons))

async def process_answer(message, user, text):
    q = user["current"]
    q["attempts"] += 1
    correct = q["correct"]

    if text == correct:
        if user["study_mode"] == "learning":
            user["score"] += 1 if q["attempts"] == 1 else 0.5
        else:
            user["score"] += 1

        user["correct"] += 1
        await ask(message, user)
    else:
        if user["study_mode"] == "learning" and q["attempts"] < 2:
            await message.answer("Try again")
            return

        user["mistakes"].append(q["word"])
        await ask(message, user)

@dp.message(Command("leaderboard"))
async def leaderboard(message: types.Message):
    if not is_teacher(message.from_user.id):
        return

    top = get_leaderboard()
    text = "🏆 Leaderboard:\n"
    for i,(name,score) in enumerate(top,1):
        text += f"{i}. {name} — {score}\n"
    await message.answer(text)

async def main():
    init_db()
    print("Bot running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())