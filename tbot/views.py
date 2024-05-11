import telebot
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
        traceback.print_exc()
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
            print(f"Произошла ошибка: {e}")
            traceback.print_exc()
            bot.send_message(call.message.chat.id, "Произошла ошибка, попробуйте снова.")


@bot.message_handler(func=lambda message: True)
def echo_message(message):
    try:
        menu(bot, message)
    except Exception as e:
        print(f"Произошла ошибка: {e}")
        traceback.print_exc()
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте снова.")

