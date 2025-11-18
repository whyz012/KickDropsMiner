import os
import json
from loader.core.paths import APP_DIR, CONFIG_FILE


class Config:
    def __init__(self):
        self.items = []
        self.chromedriver_path = None
        self.extension_path = None
        self.hide_player = False
        self.mute = True
        self.mini_player = False
        self.telegram_bot_token = ""
        self.telegram_chat_id = ""
        self.telegram_creator_link = "t.me/tataraoscoder" # Добавляем ссылку на Telegram создателя
        self.notify_events = {
            "target_time": True,
            "offline": True,
            "error": True,
            "chat_keyword": False,
            "keyword": "",  # Ключевое слово для чата
            "telegram_target_time": False, # Новое событие для Telegram
            "telegram_offline": False,     # Новое событие для Telegram
            "telegram_error": False,       # Новое событие для Telegram
        }
        self.chrome_executable_path = "" # Добавляем путь к исполняемому файлу Chrome
        self.default_drop_minutes = 120 # Добавляем значение по умолчанию для минут дропа
        self.load()

    def load(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.items = data.get("items", [])
                self.chromedriver_path = data.get("chromedriver_path")
                self.extension_path = data.get("extension_path")
                self.hide_player = data.get("hide_player", False)
                self.mute = data.get("mute", True)
                self.mini_player = data.get("mini_player", False)
                self.telegram_bot_token = data.get("telegram_bot_token", "")
                self.telegram_chat_id = data.get("telegram_chat_id", "")
                self.telegram_creator_link = data.get("telegram_creator_link", "t.me/tataraoscoder") # Загружаем ссылку на Telegram создателя
                self.notify_events = data.get("notify_events", self.notify_events)
                self.chrome_executable_path = data.get("chrome_executable_path", "") # Загружаем путь
                self.default_drop_minutes = data.get("default_drop_minutes", 120) # Загружаем значение для минут дропа

            # Гарантируем, что у каждого элемента есть ключи 'elapsed' и 'finished'
            for item in self.items:
                item.setdefault("elapsed", 0)
                item.setdefault("finished", False)
        except FileNotFoundError:
            pass

    def save(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "items": [
                        {
                            "url": item["url"],
                            "minutes": item["minutes"],
                            "elapsed": item.get("elapsed", 0),
                            "finished": item.get("finished", False),
                        }
                        for item in self.items
                    ],
                    "chromedriver_path": self.chromedriver_path,
                    "extension_path": self.extension_path,
                    "hide_player": self.hide_player,
                    "mute": self.mute,
                    "mini_player": self.mini_player,
                    "telegram_bot_token": self.telegram_bot_token,
                    "telegram_chat_id": self.telegram_chat_id,
                    "telegram_creator_link": self.telegram_creator_link, # Сохраняем ссылку на Telegram создателя
                    "notify_events": self.notify_events,
                    "chrome_executable_path": self.chrome_executable_path, # Сохраняем путь
                    "default_drop_minutes": self.default_drop_minutes, # Сохраняем значение для минут дропа
                },
                f,
                indent=4,
                ensure_ascii=False,
            )

    def add(self, url: str, minutes: int):
        # Проверяем, существует ли уже такой URL, чтобы избежать дубликатов
        if not any(item["url"] == url for item in self.items):
            self.items.append(
                {"url": url, "minutes": minutes, "elapsed": 0, "finished": False}
            )
            self.save()

    def remove(self, idx: int):
        if 0 <= idx < len(self.items):
            del self.items[idx]
            self.save()
