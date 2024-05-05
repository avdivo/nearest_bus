import random
import string

import telebot
from telebot import types
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt

from .services.menu import menu
from .services.functions import authorize
from .services.executors import ExeAddBusStop, MyRouter


TOKEN = ''
bot = telebot.TeleBot(TOKEN, threaded=False)
#
#
# # For free PythonAnywhere accounts
# # tbot = telebot.AsyncTeleBot(TOKEN)
#
@csrf_exempt
def telegram(request):
    # Эндпоинт для получения запросов от Телеграмм
    if request.META['CONTENT_TYPE'] == 'application/json':

        json_data = request.body.decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        bot.process_new_updates([update])

        return HttpResponse('<h1>Hello!</h1>')

    else:
        raise PermissionDenied


@bot.message_handler(commands=['start'])
def greet(message):
    try:
        menu(bot, message, 'Главное меню')
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте снова.")


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        try:
            user = authorize(call.from_user)
            if not user:
                # Для ботов
                raise PermissionDenied
            class_name = user.parameter.class_name
            if class_name:
                # В переменной class_name хранится название класса программы,
                # которая выполняется для этого пользователя, создаем объект,
                # одновременно запустится продолжение выполнения программы.
                executor = globals()[class_name](bot, user, call)
            else:
                # Если нет программы, сообщаем об ошибке, такого быть не должно
                print(f"Произошла ошибка 1:")
                bot.send_message(call.message.chat.id, "Запрос не обработан.")
        except Exception as e:
            print(f"Произошла ошибка 2: {e}")
            bot.send_message(call.message.chat.id, "Произошла ошибка, попробуйте снова.")


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    try:
        menu(bot, message)
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте снова.")

# def create_keyboard(user):
#     keyboard = telebot.types.InlineKeyboardMarkup()
#     selected_buses = user.get_user_attr('selected_buses') or []
#     for i in range(1, 11):
#         if i in selected_buses:
#             text = f"Bus {i} (Selected)"
#             callback_data = f"deselect_{i}"
#         else:
#             text = f"Bus {i}"
#             callback_data = f"select_{i}"
#         button = telebot.types.InlineKeyboardButton(text=text, callback_data=callback_data)
#         keyboard.add(button)
#     return keyboard
#
# @bot.message_handler(commands=['start'])
# def start_message(message):
#     user = authorize(message)
#     keyboard = create_keyboard(user)
#     bot.send_message(message.chat.id, 'Choose buses:', reply_markup=keyboard)
#
# @bot.callback_query_handler(func=lambda call: True)
# def callback_inline(call):
#     user = authorize(call.message)
#     selected_buses = user.get_user_attr('selected_buses') or []
#     if call.data.startswith('select_'):
#         bus_number = int(call.data.split('_')[1])
#         if bus_number not in selected_buses:
#             selected_buses.append(bus_number)
#         user.set_user_attr('selected_buses', selected_buses)
#     elif call.data.startswith('deselect_'):
#         bus_number = int(call.data.split('_')[1])
#         if bus_number in selected_buses:
#             selected_buses.remove(bus_number)
#         user.set_user_attr('selected_buses', selected_buses)
#     keyboard = create_keyboard(user)
#     bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Choose buses:', reply_markup=keyboard)


# Словарь, содержащий текст и состояние чекбоксов для каждого варианта ответа
# checkbox_states = {
#     'Вариант 1': False,
#     'Вариант 2': False,
#     'Вариант 3': False,
#     'Вариант 4': False,
#     'Вариант 5': False,
#     'Вариант 6': False,
#     'Вариант 7': False,
#     'Вариант 8': False,
#     'Вариант 9': False,
#     'Вариант 10': False,
#     'Вариант 11': False,
#     'Вариант 12': False,
#     'Вариант 13': False,
#     'Вариант 14': False,
#     'Вариант 15': False,
#     'Вариант 16': False,
#     'Вариант 17': False,
#     'Вариант 18': False,
#     'Вариант 19': False,
#     'Вариант 20': False,
# }
#
#
# # Обработчик команды /start
# @bot.message_handler(commands=['start'])
# def start(message):
#     markup = types.ReplyKeyboardMarkup(row_width=1)
#     for key in checkbox_states:
#         markup.add(types.KeyboardButton(key))
#     bot.send_message(message.chat.id, "Выберите один из вариантов ответа:", reply_markup=markup)
#
#
# # Обработчик нажатия на кнопки с вариантами ответа
# @bot.message_handler(func=lambda message: message.text in checkbox_states.keys())
# def handle_checkbox(message):
#     # Получаем текст кнопки и меняем состояние чекбокса
#     option = message.text
#     checkbox_states[option] = not checkbox_states[option]
#
#     # Отправляем сообщение о текущем состоянии чекбоксов
#     response = "Текущее состояние чекбоксов:\n"
#     for key, value in checkbox_states.items():
#         response += f"{key}: {'Выбрано' if value else 'Не выбрано'}\n"
#
#     bot.send_message(message.chat.id, response)





# # Список вариантов ответа. 50 вариантов для демонстрации
#
# options = dict()
# for i in range(1, 51):
#     # Сгенерируем случайный текст для варианта ответа длиной от 5 до 20 символов
#     text = ''.join(random.choices(string.ascii_letters, k=random.randint(5, 20)))
#     options.update({f'{text} {i}': False})
#
# # options = {'Вариант 1': False, 'Вариант 2': False, 'Вариант 3': False}
#
# # Функция для создания первой клавиатуры
# def create_keyboard1():
#     markup = types.InlineKeyboardMarkup(row_width=4)
#     buttons = []
#     for option, selected in options.items():
#         text = f"✓ {option}" if selected else option
#         button = types.InlineKeyboardButton(text=text, callback_data=option)
#         buttons.append(button)
#     # Добавляем кнопки в разметку по 2 в ряд
#     for i in range(0, len(buttons), 2):
#         markup.add(*buttons[i:i+2])
#     return markup
#
# # Функция для создания второй клавиатуры
# def create_keyboard2():
#     markup = types.InlineKeyboardMarkup(row_width=4)
#     buttons = []
#     for option, selected in options.items():
#         text = f"{option} ✓" if selected else option
#         button = types.InlineKeyboardButton(text=text, callback_data=option)
#         buttons.append(button)
#     # Добавляем кнопки в разметку по 2 в ряд
#     for i in range(0, len(buttons), 2):
#         markup.add(*buttons[i:i+2])
#     return markup
#
# # Обработчик команды /start
# @bot.message_handler(commands=['start'])
# def start(message):
#     markup = create_keyboard1()
#     bot.send_message(message.chat.id, 'Choose an option:', reply_markup=markup)
#
# # Обработчик нажатий на кнопки в Inline клавиатуре
# @bot.callback_query_handler(func=lambda call: True)
# def handle_callback(call):
#     option = call.data
#     options[option] = not options[option]  # Инвертируем выбор варианта
#     if '✓' in call.message.text:
#         markup = create_keyboard1()
#     else:
#         markup = create_keyboard2()
#     bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Choose an option:', reply_markup=markup)



