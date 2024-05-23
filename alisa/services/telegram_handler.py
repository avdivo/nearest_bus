import telebot
import logging

from django.conf import settings


class Messages(logging.Handler):
    """Класс для отправки сообщений логгера в ТГ."""
    def __init__(self):
        super().__init__()
        self.admin_ids = settings.ADMINS
        self.bot = telebot.TeleBot(settings.TOKEN, threaded=False)

    def emit(self, record):
        log_entry = self.format(record)
        for admin_id in self.admin_ids:
            self.bot.send_message(admin_id, log_entry)
