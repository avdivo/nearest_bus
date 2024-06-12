import telebot
import logging
import traceback

from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.db.models import Sum

from .models import BotUser, IdsForName
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


@bot.message_handler(commands=['message'])
def handle_message(message):
    bot.send_message(message.chat.id, "Напишите сообщение разработчику.")
    user = authorize(message.from_user)
    if not user:
        # Для ботов
        raise PermissionDenied
    # Работает исполнитель в классе ExeMessage
    user.parameter.class_name = 'ExeMessage'
    user.parameter.save()


@bot.message_handler(commands=['stat'])
def handle_message(message):
    """# Метод, который по команде /stat покажет
    - количество пользователей
    - сумму действий всех пользователей
    - сумму показов расписания всех пользователей
    """
    user = authorize(message.from_user)
    if not user:
        # Для ботов
        raise PermissionDenied

    if int(user.user_id) not in settings.ADMINS:
        # Спрашивает не администратор
        bot.send_message(message.chat.id, "Вы не администратор.")
        return

    user_count = BotUser.objects.count()
    action_count = BotUser.objects.aggregate(Sum('action_count'))['action_count__sum']
    schedule_count = BotUser.objects.aggregate(Sum('schedule_count'))['schedule_count__sum']
    bot.send_message(message.chat.id, f"Всего обработано запросов от всех пользователей: {action_count}\n"
                                     f"Всего показано расписаний для всех пользователей: {schedule_count}\n"
                                     f"Всего пользователей: {user_count}")


@bot.message_handler(commands=['help'])
def handle_message(message):
    user = authorize(message.from_user)
    if not user:
        # Для ботов
        raise PermissionDenied

    try:
        help_text = open(settings.BASE_DIR / 'tbot' / 'help.md', 'r')
        bot.send_message(message.chat.id, help_text.read(), parse_mode='Markdown', disable_web_page_preview=True)
    except Exception as e:
        logger.error('---' * 10)
        logger.error(f"Произошла ошибка для пользователя {message.from_user.id}: {e}")
        logger.error(traceback.format_exc())
        bot.send_message(message.chat.id, "Произошла ошибка, попробуйте снова.")


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.message:
        try:
            user = authorize(call.from_user)
            if not user:
                # Для ботов
                raise PermissionDenied

            # Если запрос от постоянной клавиатуры, то передаем управление в ее класс
            # Их работа описана в классе Executor
            kb_id, key_name = call.data.split('_')  # Получаем id клавиатуры
            class_name = IdsForName.get_name_by_id(kb_id)  # Получаем имя класса
            action = True
            if not class_name:
                class_name = user.parameter.class_name
                action = None

            if class_name:
                globals()[class_name](bot, user, call, action=action)
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
