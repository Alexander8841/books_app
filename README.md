## 📚 Books App

Веб-приложение и Telegram-бот для просмотра списка книг и добавления отзывов.
Серверная часть написана на **Flask**, взаимодействие с базой данных осуществляется через **SQLAlchemy** и **MySQL**.
Бот реализован с использованием **python-telegram-bot**.

---

### 🚀 Установка и запуск (локально)

1. Клонировать репозиторий:

   ```bash
   git clone https://github.com/Alexander8841/books_app.git
   cd books_app
   ```

2. Создать виртуальное окружение и активировать его.\
   *Linux/macOS/WSL:*
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
   
   *Windows (PowerShell):*
   ```bash
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
3. Установить зависимости:

   ```bash
   pip install -r requirements.txt
   ```

4. Создать файл `.env` в корне проекта и указать свои данные подключения:

   ```env
   DB_HOST=<your_mysql_host>
   DB_USER=<your_mysql_user>
   DB_PASSWORD=<your_mysql_password>
   DB_NAME=<your_mysql_database>
   BOT_TOKEN=<your_telegram_bot_token>
   ```
   Как получить токен бота:
   - В Telegram открыть @BotFather
   - Ввести команду /newbot и следовать инструкциям.
   - После создания бот выдаст токен.

6. Запустить веб-приложение:

   ```bash
   flask run --host=0.0.0.0 --port=5000
   ```

7. Запустить Telegram-бота:

   ```bash
   python3 bot.py
   ```

---

### ☁️ Развёртывание в облаке (Yandex Cloud) на виртуальной машине Linux

1. Подключиться к виртуальной машине:

   ```bash
   ssh -l alexander <ваш_IP_адрес>
   ```

2. Установить необходимые пакеты:

   ```bash
   sudo apt update && sudo apt upgrade -y
   sudo apt install python3 python3-pip git pkg-config libmysqlclient-dev build-essential python3-venv -y
   ```

3. Клонировать проект и развернуть окружение:

   ```bash
   git clone https://github.com/<your_username>/books_app.git
   cd books_app
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. Скопировать SSL-сертификат MySQL:

   ```bash
   mkdir -p ~/mysql_certs
   scp /path/to/root.crt alexander@<your_IP>:~/mysql_certs/
   ```

5. Создать `.env` и заполнить его по примеру выше.

6. Настроить systemd-сервисы:

   **Для Flask:**

   ```bash
   sudo nano /etc/systemd/system/books_web.service
   ```

   Вставить:

   ```ini
   [Unit]
   Description=Books Flask Web App
   After=network.target

   [Service]
   User=alexander
   WorkingDirectory=/home/alexander/books_app
   ExecStart=/home/alexander/books_app/.venv/bin/flask run --host=0.0.0.0 --port=5000
   Restart=always
   Environment=FLASK_APP=/home/alexander/books_app/app.py
   Environment=FLASK_ENV=production

   [Install]
   WantedBy=multi-user.target
   ```

   **Для Telegram-бота:**

   ```bash
   sudo nano /etc/systemd/system/books_bot.service
   ```

   Вставить:

   ```ini
   [Unit]
   Description=Books Telegram Bot
   After=network.target

   [Service]
   User=alexander
   WorkingDirectory=/home/alexander/books_app
   ExecStart=/home/alexander/books_app/.venv/bin/python3 /home/alexander/books_app/bot.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

7. Активировать и запустить сервисы:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable books_web.service books_bot.service
   sudo systemctl start books_web.service books_bot.service
   ```

---

### ✅ Проверка работы

* Веб-интерфейс: `http://<ваш_IP_адрес>:5000`
* Telegram-бот: @<username бота>

