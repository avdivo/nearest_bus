# Команда очищает таблицу вариантов имен остановок
# и добавляет в нее новые варианты имен остановок
import json

from django.core.management.base import BaseCommand
from schedule.models import OptionsForStopNames


class Command(BaseCommand):
    help = 'Добавляет варианты имен остановок'

    # Читаем варианты имен остановок из словаря файла names_bus_stops.json в корне проекта
    addition = json.load(open('names_bus_stops.json', 'r', encoding='utf-8'))

    def handle(self, *args, **options):
        OptionsForStopNames.objects.all().delete()
        for name, options in self.addition.items():
            OptionsForStopNames.objects.create(name=name, options=json.dumps(options, ensure_ascii=False))
        self.stdout.write(self.style.SUCCESS("Варианты имен остановок добавлены"))