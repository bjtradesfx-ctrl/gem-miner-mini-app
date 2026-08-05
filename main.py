import os
import asyncio
import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import uvicorn


# --- DATABASE SETUP ---
def init_db():
    """Creates the SQLite database and users table if they don't exist."""
    conn = sqlite3.connect("miner_database.db")
    cursor = conn.cursor()
    cursor.execute('''
                   CREATE TABLE IF NOT EXISTS users
                   (
                       user_id
                       INTEGER
                       PRIMARY
                       KEY,
                       points
                       REAL
                       DEFAULT
                       0.0,
                       level
                       INTEGER
                       DEFAULT
                       0
                   )
                   ''')
    conn.commit()
    conn.close()


init_db()


# --- API MODELS ---
class UserState(BaseModel):
    user_id: int
    points: float
    level: int


# --- FASTAPI & BOT SETUP ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEB_APP_URL = os.getenv("WEB_APP_URL")

app = FastAPI()


@app.get("/", response_class=HTMLResponse)
async def serve_webapp():
    with open("index.html", "r") as f:
        return f.read()


# --- SAVE & LOAD ENDPOINTS ---
@app.get("/api/load/{user_id}")
async def load_user_data(user_id: int):
    """Fetches user data from the SQLite database."""
    conn = sqlite3.connect("miner_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT points, level FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return {"points": result[0], "level": result[1]}
    return {"points": 0.0, "level": 0}


@app.post("/api/save")
async def save_user_data(state: UserState):
    """Saves or updates user data in the SQLite database."""
    conn = sqlite3.connect("miner_database.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, points, level) 
        VALUES (?, ?, ?)
    ''', (state.user_id, state.points, state.level))
    conn.commit()
    conn.close()
    return {"status": "success"}


# --- TELEGRAM BOT LOGIC ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💎 Play Gem Miner", web_app=WebAppInfo(url=WEB_APP_URL))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Welcome to the Gem Mines! Tap to mine, level up, and withdraw to your TON wallet.",
        reply_markup=reply_markup
    )


async def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    while True:
        await asyncio.sleep(3600)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(run_bot())


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)