
import json
from django.core.management.base import BaseCommand
from tbot.models import Parameter
from schedule.models import BusStop
from django.db import transaction

class Command(BaseCommand):
    """
    Команда Django для миграции данных в поле 'favorites' модели Parameter.
    Обновляет структуру избранных маршрутов пользователей:
    - Удаляет ключи 'check' и 'view'.
    - Заменяет ID остановок в полях 'start' и 'finish' на их реальные названия.
    """
    help = 'Миграция избранного в новый формат.'

    def handle(self, *args, **options):
        """
        Основной метод, выполняющий миграцию.
        """
        self.stdout.write(self.style.SUCCESS('Запуск миграции Избранного...'))

        # Для оптимизации создаем словарь {external_id: name} для всех остановок
        bus_stop_map = {stop.external_id: stop.name for stop in BusStop.objects.all()}
        
        # Получаем все параметры пользователей
        parameters = Parameter.objects.all()
        updated_users_count = 0
        updated_routes_count = 0

        for param in parameters:
            try:
                # Загружаем текущие избранные маршруты
                favorites_data = json.loads(param.favorites)
                if not isinstance(favorites_data, dict):
                    continue

                new_favorites_data = {}
                is_updated = False

                for route_name, route_details in favorites_data.items():
                    if not isinstance(route_details, dict):
                        new_favorites_data[route_name] = route_details
                        continue

                    # Удаляем старые ключи, если они существуют
                    if 'check' in route_details:
                        del route_details['check']
                        is_updated = True
                    if 'view' in route_details:
                        del route_details['view']
                        is_updated = True

                    # Обновляем 'start'
                    start_id = str(route_details.get('start', ''))
                    if start_id.isdigit() and start_id in bus_stop_map:
                        route_details['start'] = bus_stop_map[start_id]
                        is_updated = True

                    # Обновляем 'finish'
                    finish_id = str(route_details.get('finish', ''))
                    if finish_id.isdigit() and finish_id in bus_stop_map:
                        route_details['finish'] = bus_stop_map[finish_id]
                        is_updated = True
                    
                    new_favorites_data[route_name] = route_details
                    if is_updated:
                        updated_routes_count += 1

                # Если были внесены изменения, обновляем запись в БД
                if is_updated:
                    param.favorites = json.dumps(new_favorites_data, ensure_ascii=False)
                    param.save()
                    updated_users_count += 1
                    self.stdout.write(f"Обновлено избранное пользователя {param.bot_user.user_name}")

            except json.JSONDecodeError:
                self.stdout.write(self.style.WARNING(f"Не удалость прочитать избранное пользователя {param.bot_user.user_name} (ID: {param.bot_user.id}). Skipping."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка для пользователя {param.bot_user.user_name}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f'Миграция завершена. Обновлено {updated_routes_count} маршрутов для {updated_users_count} пользователей.'
        ))
