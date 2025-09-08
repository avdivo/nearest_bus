from django.core.management.base import BaseCommand
from django.conf import settings
import requests

class Command(BaseCommand):
    """
    Класс для создания management-команды Django.
    Эта команда отправляет запрос к Telegram API для установки вебхука.
    """
    help = 'Устанавливает вебхук для Telegram бота'

    def handle(self, *args, **options):
        """
        Основная логика команды.
        Вызывается при запуске `python manage.py setwebhook`.
        """
        # Проверяем, заданы ли необходимые настройки в settings.py
        try:
            # Используем TOKEN, как и в остальном проекте
            bot_token = settings.TOKEN
            webhook_host = settings.TELEGRAM_WEBHOOK_HOST
            webhook_path = settings.TELEGRAM_WEBHOOK_PATH
        except AttributeError as e:
            self.stderr.write(self.style.ERROR(
                f"Ошибка: Необходимая настройка '{e.name}' отсутствует в settings.py. "
                f"Убедитесь, что в .env заданы BOT_TOKEN, TELEGRAM_WEBHOOK_HOST и TELEGRAM_WEBHOOK_PATH, и они корректно читаются в settings.py."
            ))
            return

        # Формируем полный URL для вебхука из хоста и пути
        webhook_url = f"{webhook_host}{webhook_path}"
        
        # URL для запроса к Telegram API
        telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook?url={webhook_url}"

        self.stdout.write(f"Установка вебхука для URL: {webhook_url}...")

        try:
            # Отправляем запрос
            response = requests.get(telegram_api_url)
            # Проверяем, был ли запрос успешным (код 2xx)
            response.raise_for_status()
            
            # Проверяем ответ от Telegram
            response_data = response.json()
            if response_data.get("ok"):
                self.stdout.write(self.style.SUCCESS(
                    f"Вебхук успешно установлен! Ответ Telegram: {response_data.get('description')}"
                ))
            else:
                self.stderr.write(self.style.ERROR(
                    f"Telegram API вернул ошибку: {response_data.get('description')}"
                ))

        except requests.RequestException as e:
            # Обрабатываем возможные сетевые ошибки
            self.stderr.write(self.style.ERROR(f"Ошибка сети при установке вебхука: {e}"))
        except Exception as e:
            # Обрабатываем другие возможные ошибки
            self.stderr.write(self.style.ERROR(f"Произошла непредвиденная ошибка: {e}"))

