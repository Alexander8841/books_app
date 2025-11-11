import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, render_template, jsonify
from sqlalchemy.sql import func
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SQLALCHEMY_ENGINE_OPTIONS
from models import db, Book, Review

app = Flask(__name__)
# Подключение к MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS

db.init_app(app)  # связываем db с Flask-приложением

# --- Настройка логирования ---
# Создаём логгер
logger = logging.getLogger("books_app")
logger.setLevel(logging.DEBUG)

# Логи в файл с ротацией: 5 МБ на файл, максимум 5 файлов
file_handler = RotatingFileHandler("books_app.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Логи ошибок Flask в файл
app.logger.addHandler(file_handler)

# --- Эндпоинты ---
@app.route("/")
def index():
    try:
        books = Book.query.all()
        data = []
        for book in books:
            avg_rating = db.session.query(func.avg(Review.rating)).filter(Review.book_id == book.id).scalar()
            avg_rating = round(avg_rating, 2) if avg_rating else "Нет оценок"
            data.append({
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "average_rating": avg_rating
            })
        return render_template("index.html", books=data)
    except Exception as e:
        logger.exception("Ошибка при загрузке списка книг")
        return "Произошла ошибка", 500


@app.route("/books/<int:book_id>", methods=["GET"])
def book_detail(book_id):
    try:
        book = Book.query.get_or_404(book_id)
        reviews = Review.query.filter_by(book_id=book.id).order_by(Review.created_at.desc()).all()
        return render_template("book_detail.html", book=book, reviews=reviews)
    except Exception as e:
        logger.exception(f"Ошибка при загрузке книги {book_id}")
        return "Произошла ошибка", 500


@app.route("/books/<int:book_id>/review", methods=["POST"])
def add_review_json(book_id):
    try:
        data = request.get_json()
        rating = data.get("rating")
        review_text = data.get("review_text")

        try:
            rating = int(rating)
        except (ValueError, TypeError):
            return jsonify({"error": "Введите корректное число в поле оценки"}), 400

        if not (1 <= rating <= 5):
            return jsonify({"error": "Оценка должна быть числом от 1 до 5"}), 400

        review = Review(book_id=book_id, rating=rating, review_text=review_text)
        db.session.add(review)
        db.session.commit()

        logger.info(f"Добавлен отзыв для книги {book_id}: {rating}, {review_text}")

        return jsonify({
            "message": "Отзыв добавлен успешно",
            "review": {
                "rating": rating,
                "review_text": review_text,
                "created_at": review.created_at.strftime("%Y-%m-%d")
            }
        }), 201

    except Exception as e:
        logger.exception(f"Ошибка при добавлении отзыва для книги {book_id}")
        return jsonify({"error": "Произошла внутренняя ошибка"}), 500


# --- Глобальный обработчик ошибок ---
@app.errorhandler(404)
def page_not_found(e):
    logger.warning(f"404 - Страница не найдена: {request.path}")
    return "Страница не найдена", 404


@app.errorhandler(500)
def internal_error(e):
    logger.exception("500 - Внутренняя ошибка сервера")
    return "Внутренняя ошибка сервера", 500


# --- Запуск ---
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(host="0.0.0.0", port=5000, debug=True)
