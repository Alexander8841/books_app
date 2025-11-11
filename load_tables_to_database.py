import csv
import MySQLdb
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, SSL

conn = MySQLdb.connect(
    host=DB_HOST,
    port=3306,
    db=DB_NAME,
    user=DB_USER,
    passwd=DB_PASSWORD,
    ssl={'ca': SSL}  # путь к сертификату
)
cur = conn.cursor()

cur.execute("DELETE FROM reviews")
cur.execute("DELETE FROM books")

# Загрузка books.csv
with open(r"C:/Users/alexander/Yandex.Disk/вуз/облачные/лаба 3/books.csv", encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute(
            "INSERT INTO books (id, title, author) VALUES (%s, %s, %s)",
            (row['id'], row['title'], row['author'])
        )

# Загрузка reviews.csv
with open(r"C:/Users/alexander/Yandex.Disk/вуз/облачные/лаба 3/reviews.csv", encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cur.execute(
            "INSERT INTO reviews (id, book_id, rating, review_text, created_at) VALUES (%s, %s, %s, %s, %s)",
            (row['id'], row['book_id'], row['rating'], row['review_text'], row['created_at'])
        )

conn.commit()
conn.close()



