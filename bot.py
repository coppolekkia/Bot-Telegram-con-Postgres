import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = os.environ.get("DATABASE_URL")


def get_conn():
    """Crea una connessione a Postgres"""
    return psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS groups (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        link TEXT NOT NULL
    );
    """)
    conn.commit()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Ciao! Sono un bot di ricerca gruppi Telegram.\n\n"
        "Comandi disponibili:\n"
        "/add <nome> <link> → aggiungi un gruppo\n"
        "/list → mostra gli ultimi gruppi\n"
        "/search <termine> → cerca gruppi per nome"
    )


async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("Uso corretto: /add <nome> <link>")
        return

    name = " ".join(context.args[:-1])
    link = context.args[-1]

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO groups (name, link) VALUES (%s, %s)", (name, link))
    conn.commit()
    conn.close()

    await update.message.reply_text(f"✅ Gruppo aggiunto: {name} ({link})")


async def list_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, link FROM groups ORDER BY id DESC LIMIT 10")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("❌ Nessun gruppo salvato.")
        return

    text = "\n".join([f"🔹 {r['name']} → {r['link']}" for r in rows])
    await update.message.reply_text(text)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Uso: /search <termine>")
        return

    term = "%" + " ".join(context.args) + "%"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT name, link FROM groups WHERE name ILIKE %s LIMIT 10", (term,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("❌ Nessun gruppo trovato.")
    else:
        text = "\n".join([f"🔹 {r['name']} → {r['link']}" for r in rows])
        await update.message.reply_text(text)


def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("Variabile TELEGRAM_TOKEN mancante.")
        print("⚠️ Devi impostare TELEGRAM_TOKEN.")
        return

    if not DB_URL:
        logger.error("Variabile DATABASE_URL mancante.")
        print("⚠️ Devi impostare DATABASE_URL.")
        return

    init_db()

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("list", list_groups))
    app.add_handler(CommandHandler("search", search))

    logger.info("🤖 Bot avviato con Postgres...")
    app.run_polling()


if __name__ == "__main__":
    main()
