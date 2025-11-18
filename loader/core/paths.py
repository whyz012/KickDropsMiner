import os
import sys
import shutil
from appdirs import user_data_dir # Добавляем импорт appdirs

def _resolve_app_dir():
    """Directory that contains bundled resources/assets."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Изменено, чтобы получить родительский каталог


def _resolve_data_dir(): # Убираем resource_dir из аргументов
    """Writable directory used for config, cookies and persistent Chrome data."""
    # Используем appdirs для определения стандартной директории данных пользователя
    data_dir = user_data_dir("KickDropsMiner", "") # vendor name пусто, так как это личное приложение
    
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


def _migrate_portable_data(source_dir, destination_dir):
    """Copies existing config/cookies from the exe folder on first run of a bundled build.
    This only applies if moving from a portable executable to an appdirs-based data directory.
    """
    if source_dir == destination_dir:
        return

    print(f"Migrating data from {source_dir} to {destination_dir}")

    # Копируем config.json
    src_config = os.path.join(source_dir, "config.json")
    dst_config = os.path.join(destination_dir, "config.json")
    if os.path.exists(src_config) and not os.path.exists(dst_config):
        try:
            os.makedirs(os.path.dirname(dst_config), exist_ok=True)
            shutil.copy2(src_config, dst_config)
            print(f"Migrated config.json to {dst_config}")
        except Exception as e:
            print(f"Error migrating config.json: {e}")

    # Копируем директории cookies/ и chrome_data/
    for folder in ("cookies", "chrome_data"):
        src_folder = os.path.join(source_dir, folder)
        dst_folder = os.path.join(destination_dir, folder)
        
        if not os.path.isdir(src_folder):
            continue

        try:
            # Проверяем, существуют ли уже данные в целевой директории
            has_existing = os.path.isdir(dst_folder) and any(os.scandir(dst_folder))
        except Exception as e:
            print(f"Error checking existing data in {dst_folder}: {e}")
            has_existing = False
        
        if has_existing:
            print(f"Existing data found in {dst_folder}, skipping migration for {folder}")
            continue

        try:
            # Копируем содержимое директории
            shutil.copytree(src_folder, dst_folder, dirs_exist_ok=True)
            print(f"Migrated {folder} to {dst_folder}")
        except Exception as e:
            print(f"Error migrating {folder}: {e}")


APP_DIR = _resolve_app_dir()
DATA_DIR = _resolve_data_dir() # Вызываем без аргументов
_migrate_portable_data(os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else APP_DIR, DATA_DIR) # Передаем правильный source_dir
COOKIES_DIR = os.path.join(DATA_DIR, "cookies")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
CHROME_DATA_DIR = os.path.join(DATA_DIR, "chrome_data")

os.makedirs(COOKIES_DIR, exist_ok=True)
os.makedirs(CHROME_DATA_DIR, exist_ok=True)