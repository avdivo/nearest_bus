import os
import requests

from django.conf import settings

from .parse_md import get_section



def query_openrouter(
        prompt_name: str, 
        prompt_suffix: str, 
        model: str = "google/gemini-2.5-flash-lite-preview-06-17",
        temperature: float = 2.0
    ) -> str:
    """
    Делает запрос к OpenRouter API.
    Возвращает текстовый ответ, если он получен в течение 1 секунды.
    В противном случае — возвращает пустую строку.

    Args:
    prompt_suffix : str
        Дополнение к базовому промпту, которое будет отправлено модели.

    Return:
    str
        Ответ модели, если он получен вовремя, иначе — пустая строка.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    # Находим по названию файл с промптом, читаем его
    # --- ЧТЕНИЕ ПРОМПТА ---
    filename = f"{prompt_name}.md"
    current_path = os.getcwd()  # Получаем текущий рабочий каталог
    # Добавляем к нему относительный путь
    full_path = os.path.join(current_path, 'nb/services/AI/prompts', filename)
    print(current_path, full_path)
    try:
        with open(full_path, "r", encoding="utf-8") as file:
            file_content = file.read()
    except FileNotFoundError:
        print(f"Файл '{full_path}' не найден.")
        return ""
    
    # --- РАЗБОР ПРОМПТА ---
    system = get_section(file_content, "SYSTEM")
    content = get_section(file_content, "PROMPT")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"{content}\n\n{prompt_suffix}"}
        ],
        "temperature": temperature,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=1)
        print(response.text)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except (requests.exceptions.Timeout, requests.exceptions.RequestException):
        return ""
