# Команда читает таблицу вариантов имен остановок
# и записывает словарь в файл names_bus_stops.json в корне проекта
import json

from django.core.management.base import BaseCommand
from schedule.models import OptionsForStopNames


class Command(BaseCommand):
    help = 'Сохраняет варианты имен остановок в файл'

    def handle(self, *args, **options):
        options = OptionsForStopNames.get_dict_options_name()
        with open('names_bus_stops.json', 'w', encoding='utf-8') as f:
            json.dump(options, f, ensure_ascii=False, indent=4)
        self.stdout.write(self.style.SUCCESS("Варианты имен остановок сохранены"))