from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import os
import threading
import time
import subprocess
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Установите секретный ключ для управления сессиями


# Класс для работы с устройствами
class DeviceMonitor:
    def __init__(self, db_name):
        self.db_name = db_name
        self.notifications = []  # Храним уведомления в памяти
        self.initialize_database()

    def initialize_database(self):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                status TEXT NOT NULL
            )
        """)
        connection.commit()
        connection.close()

    def add_device(self, ip_address):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO devices (ip_address, status) VALUES (?, ?)", (ip_address, "Unknown"))
        connection.commit()
        connection.close()

    def delete_device(self, device_id):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        cursor.execute("DELETE FROM devices WHERE id = ?", (device_id,))
        connection.commit()
        connection.close()

    def update_device_status(self, ip_address, new_status):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        cursor.execute("SELECT status FROM devices WHERE ip_address = ?", (ip_address,))
        result = cursor.fetchone()
        if result and result[0] != new_status:  # Если статус изменился
            cursor.execute("UPDATE devices SET status = ? WHERE ip_address = ?", (new_status, ip_address))
            connection.commit()
            connection.close()
            self.notifications.append(f"Device {ip_address} status changed to {new_status}.")
            return True
        connection.close()
        return False

    def get_devices(self):
        connection = sqlite3.connect(self.db_name)
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM devices")
        devices = cursor.fetchall()
        connection.close()
        return devices

    def get_notifications(self):
        notifications = self.notifications[:]
        self.notifications.clear()  # Очищаем список уведомлений после передачи
        return notifications


# Инициализация системы устройств
device_monitor = DeviceMonitor("devices.db")


# Уведомления
@app.route('/notifications', methods=['GET'])
def get_notifications():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    notifications = device_monitor.get_notifications()
    return jsonify(notifications)


# Устройства
@app.route('/devices', methods=['GET'])
def get_devices():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    devices = device_monitor.get_devices()
    return jsonify(devices)


@app.route('/add_device', methods=['POST'])
def add_device():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = request.json
    ip_address = data.get('ip_address')
    if ip_address:
        device_monitor.add_device(ip_address)
        return jsonify({'message': f'Device {ip_address} added successfully!'}), 201
    return jsonify({'error': 'IP address is required!'}), 400


@app.route('/delete_device', methods=['POST'])
def delete_device():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    data = request.json
    device_id = data.get('device_id')
    if device_id:
        device_monitor.delete_device(device_id)
        return jsonify({'message': f'Device with ID {device_id} deleted successfully!'}), 200
    return jsonify({'error': 'Device ID is required!'}), 400


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password)
        connection = sqlite3.connect("devices.db")
        cursor = connection.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            connection.commit()
            connection.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            connection.close()
            return "User already exists."
    return render_template('register.html')


# Авторизация
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = sqlite3.connect("devices.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        connection.close()
        if user and check_password_hash(user[2], password):
            session['user_id'] = user[0]
            return redirect(url_for('index'))
        return "Invalid credentials."
    return render_template('login.html')


# Выход из аккаунта
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


# Главная страница
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')


# Функция для мониторинга устройств
def monitor_devices():
    while True:
        devices = device_monitor.get_devices()
        for device in devices:
            ip_address = device[1]
            new_status = ping_device(ip_address)
            device_monitor.update_device_status(ip_address, new_status)
        time.sleep(5)


# Пинг устройств
def ping_device(ip_address):
    try:
        result = subprocess.run(['ping', '-c', '1', ip_address] if os.name != 'nt' else ['ping', '-n', '1', ip_address],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return "Available" if result.returncode == 0 else "Unavailable"
    except Exception:
        return "Unavailable"


# Запускаем мониторинг устройств в отдельном потоке
threading.Thread(target=monitor_devices, daemon=True).start()


if __name__ == '__main__':
    app.run()
