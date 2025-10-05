from django.http import JsonResponse


def health_check(request):
    # Ответ на запрос о доступности сервиса
    return JsonResponse({"status": "ok"})
