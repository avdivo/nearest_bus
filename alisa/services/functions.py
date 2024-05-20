# Вспомогательные функции
from django.utils import timezone

from alisa.models import AlisaUser


def date_now():
    """Возвращает текущую дату и время в формате datetime с поправкой на часовой пояс."""
    # Определяем текущую дату с поправкой на часовой пояс
    current_timezone = timezone.get_current_timezone()
    utc_time = timezone.now()  # получаем текущую дату в UTC
    # Удаляем информацию о секундах и микросекундах
    utc_time = utc_time.replace(second=0, microsecond=0)
    date_now = utc_time.astimezone(current_timezone)  # конвертируем дату в текущий часовой пояс
    return date_now


def authorize(request_body) -> AlisaUser:
    """Автоматическая регистрация и авторизация пользователя.
    Получает сообщение от Алисы. Проверяет по application_id есть ли такое устройство.
    Если нет - добавляет.
    Возвращает объект модели пользователя.
    Обновляет время последнего входа пользователя и активен ли он.
    """
    try:
        application_id = request_body['session']['application']['application_id']
    except KeyError:
        return None  # Если нет application_id, то возвращаем None

    user = AlisaUser.objects.filter(application_id=application_id).first()
    if not user:
        # Добавляем пользователя в БД
        user = AlisaUser.objects.create(application_id=application_id)
        user.save()
    user.last_update = date_now()
    user.action_count += 1
    user.save()
    return user

