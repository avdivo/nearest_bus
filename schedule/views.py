import telebot
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
# =========================================================================================>

TOKEN = '7019444368:AAFUiHbtAvmERwxUoP_GemKTlPas2rm_DSM'
bot = telebot.TeleBot(TOKEN)


# For free PythonAnywhere accounts
# tbot = telebot.TeleBot(TOKEN, threaded=False)

@csrf_exempt
def tbot(request):
    if request.META['CONTENT_TYPE'] == 'application/json':

        json_data = request.body.decode('utf-8')
        update = telebot.types.Update.de_json(json_data)
        tbot.process_new_updates([update])

        return HttpResponse("Приветтт")

    else:
        raise PermissionDenied



