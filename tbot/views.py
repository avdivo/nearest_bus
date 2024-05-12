import json
import telebot
import logging
import traceback
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from .services.menu import menu
from .services.functions import authorize
from .services.executors import ExeAddBusStop, MyRouter, MyRouterSetting


bot = telebot.TeleBot(settings.TOKEN, threaded=False)
#
#
# # For free PythonAnywhere accounts
# # tbot = telebot.AsyncTeleBot(TOKEN)
#

# Настройка логирования
logger = telebot.logger
telebot.logger.setLevel(logging.INFO)  # или logging.DEBUG для более подробного вывода
fh = logging.FileHandler('telebot.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

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
        logger.error('---' * 10)
        logger.error(f"Произошла ошибка для пользователя {message.from_user.id}: {e}")
        logger.error(traceback.format_exc())
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте снова.")


# @bot.message_handler(commands=['message'])
# def handle_message(message):
#     text = message.text.split(' ', 1)[1] if len(message.text.split(' ', 1)) > 1 else ''
#     chat_id = message.chat.id
#     user_id = message.from_user.id
#
#     # Преобразуем строку JSON в список
#     admin_ids = settings.ADMINS
#
#     # Отправляем сообщение каждому администратору
#     for admin_id in admin_ids:
#         bot.send_message(admin_id, f"Пользователь с ID {user_id} и ID чата {chat_id} отправил сообщение: {text}")


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
                globals()[class_name](bot, user, call)
            else:
                logger.error('---' * 10)
                logger.error(f"Произошла ошибка для пользователя {call.from_user.id}:")
                bot.send_message(call.message.chat.id, "Запрос не обработан.")
        except Exception as e:

            # отделить записи в логах
            logger.error('---'*10)
            logger.error(f"Произошла ошибка для пользователя {call.from_user.id}: {e}")
            logger.error(traceback.format_exc())
            bot.send_message(call.message.chat.id, "Произошла ошибка, попробуйте снова.")

@bot.message_handler(func=lambda message: True)
def echo_message(message):
    try:
        menu(bot, message)
    except Exception as e:
        logger.error('---' * 10)
        logger.error(f"Произошла ошибка для пользователя {message.from_user.id}: {e}")
        logger.error(traceback.format_exc())
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте снова.")
