import telebot
import logging

from django.conf import settings


class Messages(logging.Handler):
    def __init__(self):
        super().__init__()
        self.admin_ids = settings.ADMINS
        self.bot = telebot.TeleBot(settings.TOKEN, threaded=False)

    def emit(self, record):
        log_entry = self.format(record)
        print(log_entry)
        for admin_id in self.admin_ids:
            self.bot.send_message(admin_id, f"Answer_to_{log_entry} ")
