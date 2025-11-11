import logging
import random
from telegram import (
    Update, InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes,
)
from config import BOT_TOKEN, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_ENGINE_OPTIONS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from models import Book, Review

# ===================== ЛОГИРОВАНИЕ =====================
logging.basicConfig(
    level=logging.WARNING,
    format='[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("books_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("books_bot")
logger.setLevel(logging.INFO)

# отключаем лишние логи из библиотек
logging.getLogger("telegram").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

# ===================== НАСТРОЙКА ORM =====================
engine = create_engine(SQLALCHEMY_DATABASE_URI, **SQLALCHEMY_ENGINE_OPTIONS)
SessionLocal = sessionmaker(bind=engine)
db = SQLAlchemy()

def get_session():
    return SessionLocal()

# ===================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====================
def review_rating_keyboard(book_id: int):
    """Кнопки для выбора рейтинга от 1 до 5"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐1", callback_data=f"setrating_{book_id}_1"),
            InlineKeyboardButton("⭐2", callback_data=f"setrating_{book_id}_2"),
            InlineKeyboardButton("⭐3", callback_data=f"setrating_{book_id}_3"),
            InlineKeyboardButton("⭐4", callback_data=f"setrating_{book_id}_4"),
            InlineKeyboardButton("⭐5", callback_data=f"setrating_{book_id}_5"),
        ]
    ])

# ===================== ОБРАБОТЧИКИ =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Главное меню"""
    context.user_data["search_mode"] = False
    message = update.message or update.callback_query.message

    keyboard = [
        [KeyboardButton("🔍 Поиск книги")],
        [KeyboardButton("⭐ Топ-10 книг")],
        [KeyboardButton("🎲 Случайная книга")],
    ]
    await message.reply_text(
        "📚 Привет! Я книжный бот.\nВыбери действие.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    logger.info(f"Пользователь {update.effective_user.id} запустил бота (/start)")

async def search_books(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Переход в режим поиска"""
    message = update.message or (update.callback_query and update.callback_query.message)
    if message:
        await message.reply_text("Введите название или автора книги (на английском):")
    context.user_data["search_mode"] = True
    logger.info(f"Пользователь {update.effective_user.id} перешёл в режим поиска")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text.strip()

    # --- Режим добавления отзыва (текст) ---
    if context.user_data.get("review_book_id") and context.user_data.get("review_rating"):
        context.user_data["search_mode"] = False
        book_id = context.user_data.pop("review_book_id")
        rating = context.user_data.pop("review_rating")
        review_text = user_text if user_text else ""
        session = get_session()
        review = Review(book_id=book_id, rating=rating, review_text=review_text)
        session.add(review)
        session.commit()
        session.close()
        logger.info(
            f"Пользователь {update.effective_user.id} добавил отзыв на книгу ID={book_id} "
            f"с оценкой {rating} и текстом: '{review_text[:50]}'"
        )
        keyboard = [
            [InlineKeyboardButton("⬅ Назад к книге", callback_data=f"book_{book_id}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
        ]
        await update.message.reply_text(
            "✅ Отзыв добавлен!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # --- Меню действий ---
    if user_text == "🔍 Поиск книги":
        await search_books(update, context)
    elif user_text == "⭐ Топ-10 книг":
        context.user_data["search_mode"] = False
        await show_top(update, context)
    elif user_text == "🎲 Случайная книга":
        context.user_data["search_mode"] = False
        await show_random(update, context)

    # --- Режим поиска ---
    elif context.user_data.get("search_mode"):
        session = get_session()
        books = session.query(Book).filter(
            (Book.title.ilike(f"%{user_text}%")) |
            (Book.author.ilike(f"%{user_text}%"))
        ).limit(10).all()
        session.close()

        logger.info(f"Пользователь {update.effective_user.id} ищет '{user_text}' — найдено {len(books)} результатов")

        if not books:
            await update.message.reply_text("Ничего не найдено 😔")
            return

        keyboard = [
            [InlineKeyboardButton(f"{b.title} — {b.author}", callback_data=f"book_{b.id}")]
            for b in books
        ]
        await update.message.reply_text("📚 Найдено:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    else:
        await update.message.reply_text("Не понял 🤔. Выберите действие.")

async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показ топ-10 книг с кнопками для перехода к деталям"""
    session = get_session()
    books = session.query(Book).options(joinedload(Book.reviews)).all()
    session.close()

    if not books:
        await update.callback_query.message.reply_text("Нет данных о книгах 😔")
        return

    books_sorted = sorted(
        books,
        key=lambda b: (sum(r.rating for r in b.reviews) / len(b.reviews)) if b.reviews else 0,
        reverse=True
    )[:10]

    msg = "🏆 <b>Топ-10 книг:</b>\n\n"
    keyboard = []

    for i, b in enumerate(books_sorted, start=1):
        avg_rating = (
            round(sum(r.rating for r in b.reviews) / len(b.reviews), 1)
            if b.reviews else "—"
        )
        book_info = f"{i}. {b.title} — {b.author} ⭐{avg_rating}\n"
        keyboard.append([InlineKeyboardButton(book_info, callback_data=f"book_{b.id}")])

    message = update.message or (update.callback_query and update.callback_query.message)
    if message:
        await message.reply_html(msg, reply_markup=InlineKeyboardMarkup(keyboard))

    logger.info(f"Пользователь {update.effective_user.id} запросил топ-10 книг")

async def show_random(update: Update, context: ContextTypes.DEFAULT_TYPE):
    session = get_session()
    all_books = session.query(Book).all()
    session.close()

    if not all_books:
        await update.callback_query.message.reply_text("Нет данных о книгах 😔")
        return

    book = random.choice(all_books)
    logger.info(f"Пользователь {update.effective_user.id} запросил случайную книгу ID={book.id}")
    await show_book_details(update, context, book.id)

def render_stars(rating: int) -> str:
    return "⭐" * rating + "☆" * (5 - rating)

async def show_book_details(update: Update, context: ContextTypes.DEFAULT_TYPE, book_id: int):
    context.user_data["search_mode"] = False
    session = get_session()
    book = session.get(Book, book_id, options=[joinedload(Book.reviews)])

    if not book:
        session.close()
        await update.callback_query.message.reply_text("Книга не найдена 😔")
        return

    avg_rating = round(sum(r.rating for r in book.reviews)/len(book.reviews), 1) if book.reviews else "—"

    text_msg = (
        f"📖 <b>{book.title}</b>\n"
        f"Автор: {book.author}\n"
        f"Оценка: ⭐{avg_rating}\n\n"
        f"💬 <b>Последние отзывы:</b>\n\n"
    )
    for r in sorted(book.reviews, key=lambda r: r.created_at, reverse=True)[:3]:
        text_msg += f"{r.created_at.strftime('%Y-%m-%d')} {render_stars(r.rating)}\n{r.review_text}\n\n"

    keyboard = [
        [InlineKeyboardButton("✍️ Оставить отзыв", callback_data=f"review_{book.id}")],
    ]

    message = update.message or (update.callback_query and update.callback_query.message)
    if message:
        await message.reply_html(text_msg, reply_markup=InlineKeyboardMarkup(keyboard))

    logger.info(f"Пользователь {update.effective_user.id} открыл книгу ID={book.id}")
    session.close()

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("book_"):
        book_id = int(data.split("_")[1])
        await show_book_details(update, context, book_id)

    elif data.startswith("review_"):
        book_id = int(data.split("_")[1])
        context.user_data["review_book_id"] = book_id
        await query.message.reply_text(
            "Поставьте оценку книге:",
            reply_markup=review_rating_keyboard(book_id)
        )
        logger.info(f"Пользователь {update.effective_user.id} начал писать отзыв для книги ID={book_id}")

    elif data.startswith("setrating_"):
        _, book_id_str, rating_str = data.split("_")
        book_id = int(book_id_str)
        rating = int(rating_str)
        context.user_data["review_book_id"] = book_id
        context.user_data["review_rating"] = rating
        keyboard = [
            [InlineKeyboardButton("Пропустить отзыв", callback_data="skip_review")]
        ]
        await query.message.reply_text(
            "Теперь напишите отзыв или нажмите кнопку 'Пропустить отзыв':",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Пользователь {update.effective_user.id} выбрал оценку {rating} для книги ID={book_id}")

    elif data == "skip_review":
        book_id = context.user_data.pop("review_book_id")
        rating = context.user_data.pop("review_rating")
        session = get_session()
        review = Review(book_id=book_id, rating=rating, review_text="")
        session.add(review)
        session.commit()
        session.close()
        keyboard = [
            [InlineKeyboardButton("⬅ Назад к книге", callback_data=f"book_{book_id}")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="back")]
        ]
        await query.message.reply_text(
            "✅ Отзыв добавлен!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info(f"Пользователь {update.effective_user.id} добавил отзыв без текста на книгу ID={book_id}")

# ===================== ЗАПУСК =====================
def main():
    logger.info("🚀 Запуск Telegram-бота...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("top", show_top))
    app.add_handler(CommandHandler("random", show_random))
    app.add_handler(CommandHandler("search", search_books))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()
