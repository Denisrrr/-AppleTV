import random
import sqlite3
from flask import Flask, render_template_string
from ping3 import ping

# Инициализация Flask-приложения
app = Flask(__name__)

# Создаем или подключаемся к базе данных
conn = sqlite3.connect('devices_status.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы для хранения IP-адресов и статусов, если её нет
cursor.execute('''CREATE TABLE IF NOT EXISTS devices
                  (id INTEGER PRIMARY KEY, address TEXT, status TEXT)''')


# Генерация случайных IP-адресов и их добавление в базу данных
def generate_random_ip():
    return f"192.168.{random.randint(0, 255)}.{random.randint(1, 255)}"


def populate_db_with_random_ips(num_ips=5):
    for _ in range(num_ips):
        address = generate_random_ip()
        cursor.execute("INSERT INTO devices (address, status) VALUES (?, ?)", (address, "Unknown"))
    conn.commit()


# Функция для пинга устройств и обновления статусов
def ping_devices():
    cursor.execute("SELECT id, address FROM devices")
    devices = cursor.fetchall()

    for device in devices:
        device_id, address = device
        response_time = ping(address)
        status = "Available" if response_time else "Unavailable"
        cursor.execute("UPDATE devices SET status=? WHERE id=?", (status, device_id))

    conn.commit()


# HTML-шаблон для отображения данных
html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Device Status</title>
    <style>
        table {
            width: 50%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 18px;
            text-align: left;
        }
        th, td {
            padding: 12px;
            border: 1px solid #ddd;
        }
        th {
            background-color: #f2f2f2;
        }
        tr:nth-child(even) {
            background-color: #f9f9f9;
        }
    </style>
</head>
<body>
    <h1>Device Status</h1>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>IP Address</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>
            {% for device in devices %}
            <tr>
                <td>{{ device[0] }}</td>
                <td>{{ device[1] }}</td>
                <td>{{ device[2] }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
</body>
</html>
"""


# Главная страница, на которой будут отображены результаты пинга
@app.route('/')
def index():
    ping_devices()  # Пингуем устройства перед показом страницы
    cursor.execute("SELECT * FROM devices")
    devices = cursor.fetchall()
    return render_template_string(html_template, devices=devices)


if __name__ == '__main__':
    # Заполняем базу данных случайными IP-адресами, если таблица пуста
    cursor.execute("SELECT COUNT(*) FROM devices")
    if cursor.fetchone()[0] == 0:
        populate_db_with_random_ips(10)

    # Запускаем Flask веб-сервер
    if __name__ == '__main__':
        app.run(debug=False)

