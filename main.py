import telebot
from telebot import types
import sqlite3

# Инициализация бота
bot = telebot.TeleBot('8020468658:AAHNH6TMcY352vcj-rwgpnHdv6uKqXmH2H0')

# Подключение к базе данных SQLite
conn = sqlite3.connect('equipment_bot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц, если они не существуют
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    role TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    status TEXT NOT NULL,
    booked_by INTEGER DEFAULT NULL
)
''')

# Предварительное заполнение базы данных
def seed_data():
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        users = [
            (1694197855, 'admin1', 'admin'),  # Админ
            (1241231233, 'user1', 'user')   # Пользователь
        ]
        cursor.executemany("INSERT INTO users (id, username, role) VALUES (?, ?, ?)", users)
        conn.commit()

seed_data()

# Функции для работы с базой данных
def fetch_all_equipment():
    cursor.execute("SELECT * FROM equipment")
    return cursor.fetchall()

def fetch_user_role(user_id):
    cursor.execute("SELECT role FROM users WHERE id=?", (user_id,))
    return cursor.fetchone()

def update_equipment_status(equip_id, new_status, user_id=None):
    cursor.execute("UPDATE equipment SET status=?, booked_by=? WHERE id=?", (new_status, user_id, equip_id))
    conn.commit()

def fetch_user_booked_equipment(user_id):
    cursor.execute("SELECT * FROM equipment WHERE booked_by=?", (user_id,))
    return cursor.fetchall()

def add_equipment(name, category):
    cursor.execute("INSERT INTO equipment (name, category, status) VALUES (?, ?, ?)", (name, category, "free"))
    conn.commit()

def delete_equipment(equip_id):
    cursor.execute("DELETE FROM equipment WHERE id=?", (equip_id,))
    conn.commit()

def edit_equipment(equip_id, new_name, new_category):
    cursor.execute("UPDATE equipment SET name=?, category=? WHERE id=?", (new_name, new_category, equip_id))
    conn.commit()

# Верификация роли пользователя
def is_admin(user_id):
    role = fetch_user_role(user_id)
    return role and role[0] == "admin"

def is_user(user_id):
    role = fetch_user_role(user_id)
    return role and role[0] == "user"

# Команда /start
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    role = fetch_user_role(user_id)

    if not role:
        bot.send_message(message.chat.id, "У вас нет доступа к системе. Обратитесь к администратору.")
    else:
        role = role[0]
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("Просмотреть оборудование", "Забронировать оборудование")
        if role == "admin":
            markup.add("Добавить оборудование", "Редактировать оборудование", "Удалить оборудование")
        if role == "user":
            markup.add("Разбронировать оборудование")
        bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:", reply_markup=markup)

# Просмотр оборудования
@bot.message_handler(func=lambda message: message.text == "Просмотреть оборудование")
def view_equipment(message):
    equipment_list = fetch_all_equipment()
    response = "Список оборудования:\n"
    for item in equipment_list:
        response += f"{item[1]} ({item[2]}) - {item[3]}\n"  # item[1]: name, item[2]: category, item[3]: status
    bot.send_message(message.chat.id, response)

# Бронирование оборудования с выбором
@bot.message_handler(func=lambda message: message.text == "Забронировать оборудование")
def choose_equipment_to_book(message):
    equipment_list = fetch_all_equipment()
    keyboard = types.InlineKeyboardMarkup()

    for item in equipment_list:
        if item[3] == 'free':  # item[3]: статус оборудования
            keyboard.add(types.InlineKeyboardButton(text=f"{item[1]} ({item[2]})", callback_data=f"book_{item[0]}"))

    if keyboard.keyboard:
        bot.send_message(message.chat.id, "Выберите оборудование для бронирования:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Все оборудование уже забронировано.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("book_"))
def book_selected_equipment(call):
    equip_id = int(call.data.split("_")[1])  # Извлекаем ID оборудования
    user_id = call.from_user.id

    update_equipment_status(equip_id, 'booked', user_id)
    bot.send_message(call.message.chat.id, "Оборудование успешно забронировано!")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# Разбронирование оборудования
@bot.message_handler(func=lambda message: message.text == "Разбронировать оборудование")
def choose_equipment_to_unbook(message):
    user_id = message.from_user.id
    user_equipment = fetch_user_booked_equipment(user_id)
    keyboard = types.InlineKeyboardMarkup()

    for item in user_equipment:
        keyboard.add(types.InlineKeyboardButton(text=f"{item[1]} ({item[2]})", callback_data=f"unbook_{item[0]}"))

    if keyboard.keyboard:
        bot.send_message(message.chat.id, "Выберите оборудование для разбронирования:", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "Вы не забронировали оборудование.")

@bot.callback_query_handler(func=lambda call: call.data.startswith("unbook_"))
def unbook_selected_equipment(call):
    equip_id = int(call.data.split("_")[1])  # Извлекаем ID оборудования
    user_id = call.from_user.id

    cursor.execute("SELECT booked_by FROM equipment WHERE id=?", (equip_id,))
    booked_by = cursor.fetchone()

    if booked_by and booked_by[0] == user_id:
        update_equipment_status(equip_id, 'free', None)
        bot.send_message(call.message.chat.id, "Оборудование успешно разбронировано!")
    else:
        bot.send_message(call.message.chat.id, "Вы не можете разбронировать это оборудование, так как вы его не бронировали.")
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)

# Обработка кнопки "Добавить оборудование"
@bot.message_handler(func=lambda message: message.text == "Добавить оборудование")
def request_add_equipment(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        msg = bot.reply_to(message, "Введите данные в формате: <название> <категория>")
        bot.register_next_step_handler(msg, process_add_equipment)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

def process_add_equipment(message):
    try:
        args = message.text.split()
        if len(args) < 2:
            bot.send_message(message.chat.id, "Ошибка: Введите данные в формате: <название> <категория>")
            return

        add_equipment(args[0], args[1])
        bot.send_message(message.chat.id, f"Добавлено оборудование: {args[0]} ({args[1]})")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")

# Обработка кнопки "Удалить оборудование"
@bot.message_handler(func=lambda message: message.text == "Удалить оборудование")
def request_delete_equipment(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        msg = bot.reply_to(message, "Введите ID оборудования для удаления")
        bot.register_next_step_handler(msg, process_delete_equipment)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

def process_delete_equipment(message):
    try:
        equip_id = int(message.text)
        delete_equipment(equip_id)
        bot.send_message(message.chat.id, f"Оборудование с ID {equip_id} удалено.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")

# Обработка кнопки "Редактировать оборудование"
@bot.message_handler(func=lambda message: message.text == "Редактировать оборудование")
def request_edit_equipment(message):
    user_id = message.from_user.id
    if is_admin(user_id):
        msg = bot.reply_to(message, "Введите данные в формате: <id> <новое_название> <новая_категория>")
        bot.register_next_step_handler(msg, process_edit_equipment)
    else:
        bot.send_message(message.chat.id, "У вас нет прав для выполнения этой команды.")

def process_edit_equipment(message):
    try:
        args = message.text.split()
        if len(args) < 3:
            bot.send_message(message.chat.id, "Ошибка: Введите данные в формате: <id> <новое_название> <новая_категория>")
            return

        equip_id, new_name, new_category = int(args[0]), args[1], args[2]
        edit_equipment(equip_id, new_name, new_category)
        bot.send_message(message.chat.id, f"Оборудование с ID {equip_id} обновлено.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Ошибка: {str(e)}")

# Запуск бота
bot.polling(none_stop=True)
