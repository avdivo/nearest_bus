import json
import numpy as np
from sklearn.cluster import DBSCAN
import pprint

# --- Настройки ---
# Входной файл с координатами остановок
COORDINATES_FILE = 'coordinates.json'
# Выходной файл для сохранения групп (кластеров)
OUTPUT_FILE = 'groups.txt'
# Максимальное расстояние в метрах для объединения остановок в одну группу
MAX_DISTANCE_METERS = 350
# Минимальное количество остановок в группе, чтобы считать ее кластером
MIN_CLUSTER_SIZE = 2
# Радиус Земли в метрах
EARTH_RADIUS_METERS = 6371000
# --- Конец настроек ---

def create_stop_clusters():
    """
    Основная функция для загрузки данных, кластеризации и сохранения результатов.
    """
    # 1. Загрузка данных
    try:
        with open(COORDINATES_FILE, 'r', encoding='utf-8') as f:
            stops = json.load(f)
    except FileNotFoundError:
        print(f"Ошибка: Файл '{COORDINATES_FILE}' не найден.")
        return
    except json.JSONDecodeError:
        print(f"Ошибка: Не удалось прочитать JSON из файла '{COORDINATES_FILE}'.")
        return

    # 2. Подготовка данных для DBSCAN
    # Преобразуем lat/lon в числа и создаем массив для scikit-learn
    coords_deg = np.array([[float(s['lat']), float(s['lon'])] for s in stops])
    # scikit-learn's haversine metric требует радианы
    coords_rad = np.radians(coords_deg)

    # 3. Настройка параметров DBSCAN
    # Преобразуем `eps` из метров в радианы для haversine метрики
    eps_rad = MAX_DISTANCE_METERS / EARTH_RADIUS_METERS

    # 4. Запуск DBSCAN
    # algorithm='ball_tree' эффективен для географических координат
    db = DBSCAN(eps=eps_rad, min_samples=MIN_CLUSTER_SIZE, algorithm='ball_tree', metric='haversine')
    db.fit(coords_rad)

    # 5. Обработка результатов
    labels = db.labels_
    clusters = {}
    # -1 в labels означает "шум" (одиночные остановки), мы их игнорируем
    for i, label in enumerate(labels):
        if label != -1:
            if label not in clusters:
                clusters[label] = []
            # Добавляем полную информацию об остановке в кластер
            clusters[label].append(stops[i])
    
    # 6. Сохранение результатов в файл
    # Преобразуем словарь кластеров в список списков
    grouped_stops = list(clusters.values())

    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write(f"# Группы близкорасположенных остановок (расстояние <= {MAX_DISTANCE_METERS} м)\n")
            f.write("# Каждая группа - это список остановок.\n\n")
            # Используем pprint для красивого вывода, который легко читается
            f.write(pprint.pformat(grouped_stops))
        
        print(f"Кластеризация завершена. Найдено {len(grouped_stops)} групп.")
        print(f"Результаты сохранены в файл: {OUTPUT_FILE}")

    except IOError as e:
        print(f"Ошибка при записи в файл '{OUTPUT_FILE}': {e}")


if __name__ == '__main__':
    create_stop_clusters()
