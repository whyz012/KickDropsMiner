import os
import time
import json
from urllib.parse import urlparse
import urllib.request
import random
import sys
from loader.core.paths import APP_DIR, CHROME_DATA_DIR # Импортируем APP_DIR и CHROME_DATA_DIR из нового модуля

from PyQt6.QtGui import QIcon


TRANSLATIONS = {
    "ru": {
        "status_ready": "Готов",
        "title_app": "KickDropMiner",
        "col_minutes": "Цель (мин)",
        "col_elapsed": "Просмотрено",
        "btn_add": "Добавить стрим",
        "btn_remove": "Удалить",
        "btn_start_queue": "Запустить Все",
        "btn_stop_sel": "Остановить",
        "btn_stop_queue": "Остановить Все",
        "btn_signin": "Cookies",
        "switch_mute": "Отключить звук",
        "switch_hide": "Скрыть плеер",
        "switch_mini": "Мини-плеер",
        "label_theme": "Тема",
        "theme_dark": "Темная",
        "theme_light": "Светлая",
        "prompt_live_url_title": "URL стрима",
        "prompt_live_url_msg": "Введите Kick URL стрима:",
        "prompt_minutes_title": "Цель (минуты)",
        "prompt_minutes_msg": "Минут для просмотра (0 = бесконечно):",
        "status_link_added": "Ссылка добавлена",
        "status_link_removed": "Ссылка удалена",
        "offline_wait_retry": "Оффлайн: {url} - ожидание повтора",
        "error": "Ошибка",
        "invalid_url": "Неверный URL.",
        "cookies_missing_title": "Отсутствуют Cookies",
        "cookies_missing_msg": "Сохраненные Cookies не найдены. Открыть браузер для входа?",
        "status_playing": "Активен: {url}",
        "queue_running_status": "Активно: {count} стрим(ов). Последнее обновление: {url}",
        "queue_finished_status": "Все стримы остановлены",
        "status_stopped": "Остановлен",
        "chrome_start_fail": "Не удалось запустить Chrome: {e}",
        "action_required": "Требуется действие",
        "sign_in_and_click_ok": "Войдите в учетную запись в окне Chrome, затем нажмите OK для сохранения Cookies.",
        "ok": "ОК",
        "cookies_saved_for": "Cookies сохранены для {domain}",
        "cannot_save_cookies": "Не удалось сохранить Cookies: {e}",
        "connect_title": "Вход",
        "open_url_to_get_cookies": "Открыть {url} для получения Cookies?",
        "all_files_filter": "Все файлы",
        "tag_live": "В ЭФИРЕ",
        "tag_paused": "ПАУЗА",
        "tag_finished": "ЗАВЕРШЕНО",
        "tag_stop": "ОСТАНОВЛЕНО",
        "retry": "Повтор",
        "btn_drops": "Drops",
        "drops_title": "Активные Drops-кампании",
        "drops_game": "Игра",
        "drops_campaign": "Кампания",
        "drops_channels": "Каналы",
        "btn_refresh_drops": "Обновить",
        "btn_add_all_channels": "Добавить все",
        "btn_remove_all_channels": "Удалить все",
        "drops_loading": "Загрузка кампаний...",
        "drops_loaded": "Найдена {count} кампания(ии)",
        "drops_error": "Ошибка при загрузке кампаний",
        "drops_no_channels": "Каналы для этой кампании не найдены",
        "drops_added": "Добавлено: {channel}",
        "drops_watch_minutes": "Минут для просмотра:",
        "drops_no_campaigns_found": "Активные кампании дропов не найдены.",
        "warning": "Внимание",
        "cannot_edit_active_stream": "Нельзя изменить длительность активного стрима. Сначала остановите его.",
        "inf_minutes": "∞",
        "btn_telegram": "Telegram",
        "telegram_settings_title": "Настройки Telegram",
        "telegram_bot_token": "Токен бота:",
        "telegram_chat_id": "ID чата:",
        "status_chat_monitoring_required": "Мониторинг чата требует дополнительной настройки",
        "btn_stats": "Статистика",
        "stats_history_log": "Открыть лог сессий",
        "stats_title": "Статистика Просмотра",
        "stats_total_time": "Общее время за {period}: {time} мин",
        "col_stream": "Стрим",
        "col_total_minutes": "Общее время (мин)",
        "drops_title": "Активные Drops",
        "cancel": "Отмена",
        "save_config": "Сохранить",
        "config_saved": "Настройки сохранены.",
        "telegram_chat_id_hint": "ID чата должен быть ID пользователя или группы, а не ID другого бота.",
        "instructions_for_manual_cookie_export": "Пожалуйста, вручную экспортируйте куки из вашего браузера в файл JSON (например, используя расширение 'EditThisCookie'), затем выберите этот файл для импорта.",
        "select_cookie_file_title": "Выберите файл с куками",
        "cookie_import_failed_or_cancelled": "Импорт куки отменен или произошла ошибка.",
        "notify_telegram_target_time": "Уведомлять о достижении цели",
        "notify_telegram_offline": "Уведомлять о переходе в оффлайн",
        "notify_telegram_error": "Уведомлять об ошибках",
        "settings_title": "Настройки",
        "today": "Сегодня",
        "week": "Неделя",
        "month": "Месяц",
        "settings_chrome_executable_path": "Путь к исполняемому файлу Chrome:",
        "settings_browse": "Обзор",
        "settings_select_browser_executable": "Выберите исполняемый файл браузера",
        "settings_hide_player": "Скрыть плеер (запускать в фоновом режиме)",
        "settings_mute_player": "Отключить звук плеера",
        "settings_mini_player": "Включить мини-плеер",
        "settings_default_drop_minutes": "Время дропа по умолчанию (мин):",
        "overall": "Всего",
        "stats_no_log_file": "Файл логов сессий не найден.",
        "loading_text": "Загрузка...",
        "btn_start_short": "Старт",
        "btn_stop_short": "Стоп",
        "btn_remove_short": "Удалить",
        "btn_retry_short": "Повтор",
        "settings_cookie_input_label": "Вставьте куки (JSON):",
        "settings_save_cookies_button": "Сохранить куки",
        "cookie_input_success": "Куки успешно сохранены!",
        "cookie_input_invalid_json": "Неверный формат JSON для куки.",
        "cookie_input_error": "Ошибка при сохранении куки из ввода.",
        "settings_check_cookies_button": "Проверить куки",
        "cookies_found": "Куки найдены и действительны для {domain}.",
        "cookies_not_found": "Куки не найдены или устарели для {domain}.",
        "settings_chromedriver_path": "Путь к Chromedriver:",
        "settings_extension_path": "Путь к расширению Chrome:",
        "settings_select_chromedriver": "Выберите chromedriver (или бинарный файл ChromeDriver)",
        "settings_select_extension": "Выберите расширение (.crx) или распакованную папку расширения",
        "chromedriver_set": "Chromedriver установлен: {path}",
        "extension_set": "Расширение установлено: {path}",
        "executables_filter": "Исполняемые файлы",
        "settings_group_title": "Настройки приложения", # Добавлен новый ключ перевода
        "invalid_minutes_value": "Значение минут для дропа должно быть числом от 0 до 999999.",
        "btn_edit_card": "Редактировать",
        "no_card_selected_for_edit": "Для редактирования выберите карточку стрима.",
        "edit_stream_url_title": "Редактировать URL стрима",
        "edit_stream_url_msg": "Введите новый URL для стрима:",
        "edit_stream_minutes_title": "Редактировать минуты просмотра",
        "edit_stream_minutes_msg": "Введите новое количество минут для просмотра (0 = бесконечно):",
        "status_card_edited": "Карточка стрима успешно отредактирована.",
        "settings_telegram_creator_link": "Ссылка на Telegram создателя:",
        "creator_link_text": "Сделано tataraoscoder (TG)", # Текст для ссылки в статус-баре
    }
}

def translate(key: str) -> str:
    """Простая функция перевода, использующая только RU."""
    return TRANSLATIONS["ru"].get(key, key)


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
    full_path = os.path.join(APP_DIR, "assets", path) 
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
