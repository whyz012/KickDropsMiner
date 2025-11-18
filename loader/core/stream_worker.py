import os
import threading
import time
import json
from datetime import datetime
import sys
import random
from plyer import notification

from selenium.webdriver.common.by import By

from loader.core.paths import APP_DIR, CHROME_DATA_DIR # Импортируем APP_DIR, CHROME_DATA_DIR
from loader.core.selenium_driver import make_chrome_driver # Импортируем make_chrome_driver
from loader.core.cookie_manager import CookieManager
from loader.core.worker_signals import WorkerSignals
from loader.core.notifier import TelegramNotifier
from loader.core.config import Config

# Удалены ненужные импорты, связанные с Playwright и helpers.make_playwright_page
from loader.utils.helpers import (
    domain_from_url,
    kick_is_live_by_api, 
    translate as t,
)

class StreamWorker(threading.Thread):
    def __init__(
        self,
        url,
        minutes_target,
        idx,
        driver_path=None,
        extension_path=None,
        hide_player=False,
        mute=True,
        mini_player=False,
        config=None,
    ):
        super().__init__(daemon=True)
        self.url = url
        self.minutes_target = minutes_target
        self.idx = idx
        self.stop_event = threading.Event()
        self.elapsed_seconds = 0
        self.driver = None  # Будет хранить объект Selenium WebDriver
        self.driver_path = driver_path
        self.extension_path = extension_path
        self.hide_player = hide_player
        self.mute = mute
        self.mini_player = mini_player
        self.completed = False
        self._last_live_check = 0.0
        self._last_live_value = True
        self._live_check_interval = 10  # seconds
        self.signals = WorkerSignals()
        self.config = (
            config if config is not None else Config()
        )
        self.telegram_notifier = None
        print(f"Worker {self.idx}: Инициализирован для URL: {self.url}") # Добавлено логирование
        # self.app_instance = None # Сохраняем ссылку на экземпляр App

    def _save_session_log(self, success: bool, reason: str):
        log_file = os.path.join(APP_DIR, "session_log.json")
        with open(log_file, "a", encoding="utf-8") as f:
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "stream_url": self.url,
                "minutes_target": self.minutes_target,
                "elapsed_seconds": self.elapsed_seconds,
                "success": success,
                "reason": reason,
            }
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def _send_notifications(self, event: str, message: str):
        """Utility для отправки десктопных и Telegram уведомлений."""

        # 1. Десктопное Уведомление (plyer)
        if self.config.notify_events.get(event, False):
            try:
                # Определяем базовый путь для ресурсов
                if getattr(sys, "frozen", False):
                    # Мы работаем как PyInstaller bundle
                    base_path = sys._MEIPASS
                else:
                    # Мы работаем как обычный Python скрипт
                    base_path = APP_DIR

                # Для Windows notification.notify лучше использовать .ico
                icon_path = os.path.join(base_path, "assets", "icons.ico") if getattr(sys, "frozen", False) else os.path.join(base_path, "assets", "icon.svg")

                # Обрезаем сообщение, если оно слишком длинное для Windows Balloon Tip (максимум 256 символов)
                truncated_message = message[:250] + "..." if len(message) > 250 else message

                notification.notify(
                    title=f"KickDrop Miner: {event.upper()}",
                    message=truncated_message, # Используем обрезанное сообщение
                    app_name="Kick Drop Miner",
                    timeout=10,
                    # Для Windows notification.notify лучше использовать .ico
                    app_icon=os.path.join(base_path, "assets", "icons.ico"), # Всегда пытаемся использовать .ico для Windows
                )
            except Exception as e:
                print(f"Ошибка при отправке десктопного уведомления (с иконкой): {e}")

        # 2. Telegram Уведомление
        if self.config.telegram_bot_token and self.config.telegram_chat_id and self.telegram_notifier:
            telegram_event_key = f"telegram_{event}" # Создаем ключ для проверки в notify_events
            if self.config.notify_events.get(telegram_event_key, False):
                # Используем HTML для форматирования в Telegram
                telegram_message = f"<b>{event.upper()}</b>\n{message}"
                self.telegram_notifier.send_notification(telegram_message)

    def run(self):
        print(f"Worker {self.idx}: Запущен run() метод.") # Добавлено логирование
        domain = domain_from_url(self.url)
        try:
            # If loading a .crx, Chrome cannot be headless
            use_headless = bool(self.hide_player)
            # If mini_player enabled, force visible to show the small window
            if self.mini_player:
                use_headless = False
            # If hide_player enabled, force headless to hide the entire window (unless mini_player has priority)
            if self.extension_path and self.extension_path.endswith(".crx"):
                use_headless = False

            print(f"Worker {self.idx}: Создаем драйвер Chrome (headless={use_headless}).") # Добавлено логирование
            self.driver = make_chrome_driver(
                headless=use_headless,
                driver_path=self.driver_path,
                extension_path=self.extension_path,
            )

            if not use_headless and self.mini_player:
                try:
                    self.driver.set_window_size(360, 360)
                    self.driver.set_window_position(20, 20)
                    print(f"Worker {self.idx}: Установлены размеры и позиция окна для мини-плеера.") # Добавлено логирование
                except Exception as e:
                    print(f"Worker {self.idx}: Ошибка при установке размеров/позиции окна: {e}") # Логирование ошибки
                    pass

            base = f"https://{domain}" if domain else "about:blank"
            if domain:
                print(f"Worker {self.idx}: Загружаем базовый URL: {base}") # Добавлено логирование
                self.driver.get(base)
                CookieManager.load_cookies(self.driver, domain)
                print(f"Worker {self.idx}: Загружены куки для домена: {domain}") # Добавлено логирование
            print(f"Worker {self.idx}: Загружаем целевой URL: {self.url}") # Добавлено логирование
            self.driver.get(self.url)

            try:
                self.ensure_player_state()
                print(f"Worker {self.idx}: Состояние плеера установлено.") # Добавлено логирование
            except Exception as e:
                print(f"Worker {self.idx}: Ошибка при установке состояния плеера: {e}") # Логирование ошибки
                pass

            last_report = 0
            finish_reason = "Unknown reason" # Инициализация finish_reason
            print(f"Worker {self.idx}: Запускаем основной цикл мониторинга.") # Добавлено логирование
            while not self.stop_event.is_set():
                live = self.is_stream_live()
                if not live and self._last_live_value: # Стрим только что перешел в офлайн
                    print(f"Worker {self.idx}: Стрим {self.url} перешел в офлайн. Завершаем работу.")
                    self._send_notifications("offline", f"Стрим {self.url} перешел в офлайн.")
                    self._save_session_log(success=False, reason="Stream Offline")
                    finish_reason = "Stream Offline" # Устанавливаем причину завершения
                    self.stop_event.set() # Устанавливаем stop_event, чтобы выйти из цикла
                    break
                self._last_live_value = live # Обновляем последнее состояние live

                try:
                    self.ensure_player_state()
                except Exception:
                    pass
                if live:
                    self.elapsed_seconds += 1
                if time.time() - last_report >= 1:
                    last_report = time.time()
                    self.signals.update.emit(self.idx, self.elapsed_seconds, live)
                    minutes_target_seconds = self.minutes_target * 60
                    self.signals.progress_update.emit(self.idx, self.elapsed_seconds, minutes_target_seconds) # Отправляем сигнал для обновления прогресс-бара
                if (
                    self.minutes_target
                    and self.elapsed_seconds >= self.minutes_target * 60
                ):
                    self.completed = True
                    # 1. Достижение целевого времени:
                    notification_message = f"Цель достигнута: {self.minutes_target} мин. для {self.url}"
                    self._send_notifications("target_time", notification_message)
                    self._save_session_log(success=True, reason="Target Reached")
                    finish_reason = "Target Reached" # Устанавливаем причину завершения
                    print(f"Worker {self.idx}: Цель просмотра достигнута, завершаем работу.") # Добавлено логирование
                    break
                time.sleep(1) # Уменьшаем интервал до 1 секунды для более точного отсчета
            else: # Убедимся, что else относится к while, не к if
                # If loop completed without break (i.e. stop_event was set)
                # Причина остановки уже должна быть установлена, если мы здесь из-за офлайна
                if not self.completed and finish_reason == "Unknown reason": # Если не завершено по достижении цели и причина не установлена
                    self._save_session_log(success=False, reason="Stopped by user")
                    finish_reason = "Stopped by user" # Устанавливаем причину завершения
                    print(f"Worker {self.idx}: Цикл завершен по запросу остановки (stop_event).") # Добавлено логирование

        except Exception as e:
            error_msg = f"Worker {self.idx} ({self.url}) error: {type(e).__name__}: {e}"
            print(f"Worker {self.idx}: Критическая ошибка: {error_msg}") # Добавлено логирование
            self.signals.error.emit(error_msg)
            # 3. Критическая ошибка:
            notification_message = (
                f"Критическая ошибка для {self.url}: {type(e).__name__} - {e}"
            )
            self._send_notifications("error", notification_message)
            self._save_session_log(success=False, reason="Critical Error")
            finish_reason = "Critical Error" # Устанавливаем причину завершения
        finally:
            print(f"Worker {self.idx}: Запущен блок finally.") # Добавлено логирование
            try:
                if self.driver and self.driver.session_id: # Проверяем, что драйвер активен
                    print(f"Worker {self.idx}: Попытка сохранения куки.") # Добавлено логирование
                    CookieManager.save_cookies(self.driver, domain)
                    print(f"Worker {self.idx}: Куки успешно сохранены.") # Добавлено логирование
            except Exception as e:
                print(f"Worker {self.idx}: Ошибка при сохранении куки в finally: {e}") # Логирование ошибки
            try:
                if self.driver:
                    print(f"Worker {self.idx}: Попытка закрытия драйвера.") # Добавлено логирование
                    self.driver.quit()
                    print(f"Worker {self.idx}: Драйвер успешно закрыт.") # Добавлено логирование
            except Exception as e:
                print(f"Worker {self.idx}: Ошибка при закрытии драйвера в finally: {e}") # Логирование ошибки
                pass
            if self.telegram_notifier:
                try:
                    print(f"Worker {self.idx}: Закрываем сессию TelegramNotifier.") # Добавлено логирование
                    self.telegram_notifier.close_session() # Изменено на close_session
                except Exception as e:
                    print(f"Worker {self.idx}: Ошибка при закрытии сессии TelegramNotifier: {e}") # Логирование ошибки
                    pass
            
            # Передаем причину завершения через сигнал finish
            # finish_reason уже должна быть установлена к этому моменту
            # if self.completed:
            #     finish_reason = "Target Reached"
            # elif self.stop_event.is_set():
            #     finish_reason = "Stopped by user" # Если причина не была установлена ранее
            # else:
            #     finish_reason = "Unknown reason"

            self.signals.finish.emit(self.idx, self.elapsed_seconds, self.completed, finish_reason)
            self.signals.progress_update.emit(self.idx, self.elapsed_seconds, self.minutes_target * 60) # Убедимся, что прогресс-бар обновлен в конце
            print(f"Worker {self.idx}: Метод run() завершен. Причина: {finish_reason}") # Добавлено логирование

    def stop(self):
        print(f"Worker {self.idx}: Получен сигнал остановки. Устанавливаем stop_event.") # Добавлено логирование
        self.stop_event.set()
        if self.driver:
            try:
                print(f"Worker {self.idx}: Попытка закрыть драйвер в stop().") # Добавлено логирование
                self.driver.quit()
                print(f"Worker {self.idx}: Драйвер успешно закрыт в stop().") # Добавлено логирование
            except Exception as e:
                print(f"Worker {self.idx}: Ошибка при закрытии драйвера в stop(): {e}") # Логирование ошибки
                pass
            else:
                print(f"Worker {self.idx}: Драйвер не активен в stop().") # Добавлено логирование

    def is_stream_live(self):
        now = time.time()
        # Cache API checks to reduce rate-limit risk
        if now - self._last_live_check < self._live_check_interval:
            return self._last_live_value
        try:
            # Combine API + fallback DOM
            if kick_is_live_by_api(self.url):
                self._last_live_value = True
                return True
            body = self.driver.find_element(By.TAG_NAME, "body").text
            self._last_live_value = "LIVE" in body.upper()
            return self._last_live_value
        except Exception:
            self._last_live_value = False
            return False
        finally:
            # Add slight jitter to desync multiple workers
            self._live_check_interval = 10  # Убираем jitter, так как интервал уже фиксирован
            self._last_live_check = now

    def ensure_player_state(self):
        try:
            hide = "true" if self.hide_player else "false"
            muted = "true" if self.mute else "false"
            volume = "0" if self.mute else "1"
            mini = "true" if (not self.hide_player and self.mini_player) else "false"
            js = f"""
            (function(){{
              var v = document.querySelector('video');
              if (v) {{
                try {{ v.muted = {muted}; v.volume = {volume}; }} catch(e) {{}}
                if ({hide}) {{
                  v.style.opacity='0';
                  v.style.width='1px';
                  v.style.height='1px';
                  v.style.position='fixed';
                  v.style.bottom='0';
                  v.style.right='0';
                  v.style.pointerEvents='none';
                }} else if ({mini}) {{
                  v.style.opacity='1';
                  v.style.width='100px';
                  v.style.height='100px';
                  v.style.position='fixed';
                  v.style.bottom='6px';
                  v.style.right='6px';
                  v.style.pointerEvents='none';
                  v.style.zIndex='999999';
                }} else {{
                  v.style.opacity='';
                  v.style.width='';
                  v.style.height='';
                  v.style.position='';
                  v.style.bottom='';
                  v.style.right='';
                  v.style.pointerEvents='';
                }}
              }}
            }})();
            """
            self.driver.execute_script(js)
        except Exception:
            pass
