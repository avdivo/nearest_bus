import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from alisa.services.functions import authorize
from alisa.services.greetings import greetings
from utils.telegram_handler import Messages

from .services.talk_to_alisa import answer_to_alisa

# Настройка логгера c именем 'alisa' для отправки сообщений в ТГ
logger = logging.getLogger("alisa")
handler = Messages()
logger.addHandler(handler)


@csrf_exempt
def alisa(request):
    """Эндпоинт для получения запросов от Алисы."""
    request_body = json.loads(request.body)
    to_telegram = True  # Выводить логи в Телеграмм
    # print(json.dumps(request_body, indent=4, ensure_ascii=False))

    # Авторизация пользователя
    user = authorize(request_body)
    if not user:
        return

    # Если это начало сессии просто приветствие
    new = request_body["session"]["new"]
    if new:
        if request_body["request"]["original_utterance"] == "ping":
            to_telegram = False
        print()
        text = greetings(user)  # Текст приветствия
    else:
        text = answer_to_alisa(request_body)

    answer = {
        "response": {
            "text": text,
            "tts": text,
            "end_session": False,
        },
        "version": "1.0",
    }

    # Отправка сообщения в ТГ
    if to_telegram:
        logger.warning(f"{text}")

    return HttpResponse(json.dumps(answer))


@csrf_exempt
def gas(request):
    """Эндпоинт для получения запросов от Алисы."""
    request_body = json.loads(request.body)
    to_telegram = True  # Выводить логи в Телеграмм
    print(json.dumps(request_body, indent=4, ensure_ascii=False))

    return HttpResponse(True)
    # return HttpResponse(json.dumps(answer))
