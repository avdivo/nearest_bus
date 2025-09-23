"""
Скрипт для обработки файла 'Координаты остановок.xlsx'.

Читает Excel-файл с остановками, извлекает название, идентификатор и координаты,
удаляет дубликаты по названию остановки, преобразует их в список словарей
и сохраняет в JSON-файл 'coordinates.json'.

Формат словаря:
{
    "name": "Остановка 1",
    "id": "123",
    "lat": 53.0357842,
    "lon": 27.5599719
}
"""

import pandas as pd
import json
import os

def parse_coordinates(coord_str: str) -> tuple[float, float]:
    """
    Преобразует строку координат 'lat, lon' в кортеж из двух float.
    """
    try:
        lat_str, lon_str = coord_str.split(',')
        return float(lat_str.strip()), float(lon_str.strip())
    except Exception as e:
        raise ValueError(f"Невозможно распарсить координаты: '{coord_str}'") from e

def process_excel(file_path: str) -> list[dict]:
    """
    Читает Excel-файл и возвращает список словарей с уникальными остановками.
    """
    print(file_path)
    df = pd.read_excel(file_path)

    # Удаляем дубликаты по названию остановки, оставляя первую встреченную
    df = df.drop_duplicates(subset=[df.columns[0]])

    stops = []
    for _, row in df.iterrows():
        name = str(row.iloc[0]).strip()
        stop_id = str(row.iloc[1]).strip()
        lat, lon = str(row.iloc[2]).strip().split(", ")

        stop = {
            "name": name,
            "id": stop_id,
            "lat": lat,
            "lon": lon
        }
        stops.append(stop)

    return stops

def save_to_json(data: list[dict], output_path: str):
    """
    Сохраняет список словарей в JSON-файл.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # Путь к Excel-файлу
    excel_file = "stop_coord.xlsx"

    # Путь к JSON-файлу
    json_file = os.path.join(os.path.dirname(excel_file), "coordinates.json")

    # Обработка и сохранение
    try:
        stop_list = process_excel(excel_file)
        save_to_json(stop_list, json_file)
        print(f"✅ Сохранено {len(stop_list)} уникальных остановок в файл: {json_file}")
    except Exception as e:
        raise
        print(f"❌ Ошибка: {e}")
