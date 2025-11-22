import os
import time
import json
from urllib.parse import urlparse
import urllib.request
import random
import sys
from loader.core.paths import APP_DIR, CHROME_DATA_DIR # Импортируем APP_DIR и CHROME_DATA_DIR из нового модуля
from loader.core.config import Config # Импортируем Config

from PyQt6.QtGui import QIcon

_current_translations = {}
_current_locale = "en"
_config_instance = None # Будет хранить экземпляр Config

def set_locale(locale_code: str):
    global _current_translations, _current_locale
    locale_file = os.path.join(APP_DIR, "loader", "assets", "locales", f"{locale_code}.json")
    if getattr(sys, "frozen", False): # Проверяем, если мы в PyInstaller бандле
        # В режиме PyInstaller, APP_DIR уже указывает на корень, а файлы локали будут внутри loader/assets/locales
        locale_file = os.path.join(sys._MEIPASS, "loader", "assets", "locales", f"{locale_code}.json")

    if os.path.exists(locale_file):
        try:
            with open(locale_file, "r", encoding="utf-8") as f:
                _current_translations = json.load(f)
            _current_locale = locale_code
            print(f"Загружены переводы для локали: {locale_code}")
        except Exception as e:
            print(f"Ошибка загрузки файла локализации {locale_file}: {e}")
            _current_translations = {}
    else:
        print(f"Файл локализации не найден: {locale_file}")
        _current_translations = {}

def initialize_translator(config: Config):
    global _config_instance
    _config_instance = config
    set_locale(config.locale)

def translate(key: str) -> str:
    """Функция перевода, загружающая переводы из JSON-файлов.
    Использует текущую локаль из Config.
    """
    if not _config_instance: # Если конфиг еще не инициализирован, используем заглушку
        return key

    # Пытаемся получить перевод из текущей загруженной локали
    translated_text = _current_translations.get(key)
    if translated_text is not None:
        return translated_text

    # Если перевод не найден в текущей локали, пробуем английскую (en) как резервную
    if _current_locale != "en":
        en_locale_file = os.path.join(APP_DIR, "loader", "assets", "locales", "en.json")
        if getattr(sys, "frozen", False):
            en_locale_file = os.path.join(sys._MEIPASS, "loader", "assets", "locales", "en.json")
        if os.path.exists(en_locale_file):
            try:
                with open(en_locale_file, "r", encoding="utf-8") as f:
                    en_translations = json.load(f)
                translated_text = en_translations.get(key)
                if translated_text is not None:
                    return translated_text
            except Exception as e:
                print(f"Ошибка загрузки резервного файла локализации en.json: {e}")

    # Если нигде не найдено, возвращаем сам ключ
    return key


def domain_from_url(url):
    p = urlparse(url)
    return p.netloc


def kick_is_live_by_api(url: str) -> bool:
    """Returns True if the Kick channel is live (via Go API check - now always Python fallback)."""
    return _kick_is_live_by_api_python(url)


def _kick_is_live_by_api_python(url: str) -> bool:
    """Original Python implementation for checking live status (fallback)."""
    try:
        p = urlparse(url)
        if "kick.com" not in p.netloc:
            return False
        username = p.path.strip("/").split("/")[0]
        if not username:
            return False
        api_url = f"https://kick.com/api/v2/channels/{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Connection": "keep-alive",
        }
        req = urllib.request.Request(api_url, headers=headers)
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.load(resp)
            livestream = data.get("livestream")
            is_live = bool(livestream and livestream.get("is_live"))
            end_time = time.time()
            return is_live
    except Exception as e:
        print(f"Ошибка при проверке статуса стрима: {e}")
        return False

def get_icon(path):
    # Исправлено: APP_DIR указывает на корневой каталог проекта.
    # Иконка находится в loader/assets, поэтому добавляем 'loader' в путь.
    full_path = os.path.join(APP_DIR, "loader", path) 
    icon = QIcon(full_path)
    return icon

def get_headers():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Connection": "keep-alive",
    }
    return headers

def get_full_server_url(path):
    base_url = "https://api.kick.com"  # Replace with actual server URL
    return f"{base_url}/{path.lstrip('/')}"

def get_server_info():
    return {"version": "1.0.0"}
