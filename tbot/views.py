import telebot
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.views.decorators.csrf import csrf_exempt


TOKEN = ''
tbot = telebot.TeleBot(TOKEN, threaded=False)


# For free PythonAnywhere accounts
# tbot = telebot.AsyncTeleBot(TOKEN)

@csrf_exempt
def bot(request):
    if request.META['CONTENT_TYPE'] == 'application/json':

        print("Приходит")
        json_data = request.body.decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        tbot.process_new_updates([update])

        return HttpResponse('<h1>Ты подключился!</h1>')

    else:
        raise PermissionDenied


@tbot.message_handler(func=lambda message: True)
def echo_message(message):
    tbot.reply_to(message, message.text)
