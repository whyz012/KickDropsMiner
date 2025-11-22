from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea, QFrame
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSlot, QMetaObject, Q_ARG
from PyQt6.QtGui import QFont, QDesktopServices, QPixmap, QImage # Импортируем QPixmap и QImage здесь
from loader.utils.helpers import translate as t
from loader.ui.collapsible_group import CollapsibleGroup
import threading
import time
import json
import urllib.request
from io import BytesIO
from PIL import Image # Для обработки изображений
from selenium.webdriver.common.by import By

from loader.core.selenium_driver import make_chrome_driver # Импортируем make_chrome_driver
from loader.core.cookie_manager import CookieManager # Импортируем CookieManager
from loader.core.paths import APP_DIR, CHROME_DATA_DIR # Импортируем APP_DIR и CHROME_DATA_DIR
import os # Импортируем os для проверки существования файла


def fetch_drop_campaigns(config=None):
    """Fetches active drop campaigns from the Kick API.
     Uses undetected_chromedriver to bypass Cloudflare and handle compression.
    """
    driver = None
    try:
        api_url = "https://web.kick.com/api/v1/drops/campaigns"

        print(f"Fetching drops...")

        # ONLY for fetching campaigns: uses a small off-screen window
        # (headless is detected by Kick, so we use a real window but hidden)
        # Note: StreamWorkers use their own user-configured parameters
        driver = make_chrome_driver(
            headless=False, visible_width=400, visible_height=300,
            driver_path=config.chromedriver_path if config else None,
            extension_path=config.extension_path if config else None,
        )

        # Position the window off-screen to make it invisible
        try:
            driver.set_window_position(-2000, -2000)
        except:
            pass
        
        # Visit kick.com and load cookies
        print("Establishing Session on kick.com...")
        driver.get("https://kick.com")
        time.sleep(1)

        # Load saved cookies
        cookie_path = CookieManager.cookie_file_for_domain("kick.com")
        if os.path.exists(cookie_path):
            print("Loading saved cookies...")
            with open(cookie_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            for cookie in cookies:
                try:
                    if "expiry" in cookie and cookie["expiry"] is None:
                        del cookie["expiry"]
                    driver.add_cookie(cookie)
                except:
                    pass
            driver.refresh()
            time.sleep(1)

        # Use JavaScript to make the fetch request from the page context
        print(f"Fetching Drops from API...")

        fetch_script = f"""
        return fetch('{api_url}', {{
            method: 'GET',
            headers: {{
                'Accept': 'application/json',
            }},
            credentials: 'include'
        }})
        .then(response => response.text())
        .then(data => data)
        .catch(error => JSON.stringify({{error: error.toString()}}));
        """

        # Execute the script and get the result
        page_text = driver.execute_script(fetch_script)

        # Check if blocked
        if "blocked by security policy" in page_text.lower():
            print(f"Request blocked! Response: {page_text}")
            return []

        # Parse le JSON
        response = json.loads(page_text)
        print(f"Successfully fetched campaign data!")
        print(f"We have found {len(response.get('data', []))} campaigns")

        # Return data AND driver (to load images)
        campaigns = []
        data = response.get("data", [])

        if isinstance(data, list):
            for campaign in data:
                # Extract relevant information
                category = campaign.get("category", {})
                campaign_info = {
                    "id": campaign.get("id"),
                    "name": campaign.get("name", "Unknown Campaign"),
                    "game": category.get("name", "Unknown Game"),
                    "game_slug": category.get("slug", ""),
                    "game_image": category.get("image_url", ""),
                    "status": campaign.get("status", "unknown"),
                    "starts_at": campaign.get("starts_at"),
                    "ends_at": campaign.get("ends_at"),
                    "rewards": campaign.get("rewards", []),
                    "channels": [],
                }

                # Get participating channels
                channels = campaign.get("channels", [])
                for channel in channels:
                    if isinstance(channel, dict):
                        slug = channel.get("slug")
                        user = channel.get("user", {})
                        username = user.get("username") or slug
                        if slug:
                            campaign_info["channels"].append(
                                {
                                    "slug": slug,
                                    "username": username,
                                    "url": f"https://kick.com/{slug}",
                                    "profile_picture": user.get("profile_picture", ""),
                                }
                            )

                # Only add campaigns with at least one channel
                if campaign_info["channels"] or campaign.get("status") == "active":
                    campaigns.append(campaign_info)

        # Возвращаем кампании и драйвер, чтобы использовать его для загрузки изображений
        return {"campaigns": campaigns, "driver": driver}
    except Exception as e:
        print(f"Error fetching drop campaigns: {e}")
        import traceback
        traceback.print_exc()
        return {"campaigns": [], "driver": None}


class DropsWindow(QMainWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_app = parent
        self.t = t
        self._is_closed = False
        self.setWindowTitle(self.t("drops_title"))
        self.setGeometry(200, 200, 1000, 700)
        self.setMinimumSize(900, 600)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        # Теперь DropWindow использует стили из главного приложения
        self.parent_app._load_stylesheet() # Загружаем стили из главного приложения
        self.setStyleSheet(self.parent_app.styleSheet()) # Применяем стили главного приложения

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        self.status_label = QLabel(self.t("drops_loading"))
        self.status_label.setObjectName("StatusLabel")
        header_layout.addWidget(self.status_label)
        header_layout.addStretch(1)

        btn_refresh = QPushButton(self.t("btn_refresh_drops"))
        btn_refresh.setObjectName("RefreshButton")
        btn_refresh.clicked.connect(self._fetch_and_display)
        btn_refresh.setFixedWidth(180)
        header_layout.addWidget(btn_refresh)
        main_layout.addWidget(header_widget)

        # Scrollable Area for Campaigns
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        # self.setStyleSheet(self.styleSheet() + """
        #     QLabel#StatusLabel {
        #         color: #E0E0E0;
        #         font-size: 12pt;
        #         font-weight: 500;
        #     }
        #     QPushButton#RefreshButton, QPushButton#AddAllButton {
        #         background-color: #505050;
        #         border: none;
        #         color: white;
        #         padding: 8px 15px;
        #         border-radius: 5px;
        #     }
        #     QPushButton#RefreshButton:hover, QPushButton#AddAllButton:hover {
        #         background-color: #606060;
        #     }
        #     QPushButton#DropActionButton {
        #         background-color: #505050;
        #         border: none;
        #         color: white;
        #         border-radius: 5px;
        #         padding: 5px;
        #     }
        #     QPushButton#DropActionButton:hover {
        #         background-color: #606060;
        #     }
        #     QFrame {
        #         background-color: #282828;
        #         border: 1px solid #3A3A3A;
        #         border-radius: 5px;
        #     }
        # """
        # )

        self._fetch_and_display()

    def _fetch_and_display(self):
        QMetaObject.invokeMethod(
            self.status_label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.t("drops_loading"))
        )
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

        # Запускаем получение кампаний в отдельном потоке
        def run_fetch():
            result = fetch_drop_campaigns(config=self.parent_app.config_data)
            # Проверяем, не было ли окно закрыто до вызова слота
            if self._is_closed:
                return
            
            campaigns = result.get("campaigns", [])
            driver = result.get("driver")

            QMetaObject.invokeMethod(
                self,
                "_display_campaigns_slot",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(list, campaigns),
                Q_ARG(object, driver) # Передаем драйвер для загрузки изображений
            )
        threading.Thread(target=run_fetch, daemon=True).start()

    @pyqtSlot(list, object)
    def _display_campaigns_slot(self, campaigns, driver):
        try:
            self._display_campaigns(campaigns, driver)
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    @pyqtSlot(QPixmap, str) # Изменено: теперь принимает QPixmap и имя виджета (строка)
    def _set_reward_image_slot(self, pixmap, label_name):
        label = self.findChild(QLabel, label_name) # Находим QLabel по имени
        if label:
            label.setPixmap(pixmap)

    def _load_reward_image_async(self, reward_img_url, reward_label_name):
        try:
            req = urllib.request.Request(
                reward_img_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://kick.com/"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                img_data = response.read()

            # Загружаем изображение напрямую в QImage
            q_image = QImage()
            q_image.loadFromData(img_data)

            if q_image.isNull():
                print(f"Ошибка: Не удалось загрузить изображение из URL: {reward_img_url}")
                return

            # Масштабируем QImage
            scaled_q_image = q_image.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            pixmap = QPixmap.fromImage(scaled_q_image)

            QMetaObject.invokeMethod(
                self,
                "_set_reward_image_slot",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(QPixmap, pixmap),
                Q_ARG(str, reward_label_name) # Передаем имя виджета (строка)
            )
        except Exception as e:
            print(f"Ошибка загрузки изображения награды: {e}")

    def _is_channel_in_list(self, url):
        return any(item["url"] == url for item in self.parent_app.config_data.items)

    def _add_drop_channel(self, url):
        self.parent_app.config_data.add(url, self.parent_app.config_data.default_drop_minutes)
        QMetaObject.invokeMethod(self.parent_app, "refresh_list", Qt.ConnectionType.QueuedConnection)
        QMetaObject.invokeMethod(
            self.parent_app.status_label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.t("drops_added").format(channel=url.split("/")[-1]))
        )

    def _remove_drop_channel(self, url):
        try:
            idx_to_remove = next(
                i
                for i, item in enumerate(self.parent_app.config_data.items)
                if item["url"] == url
            )
            self.parent_app.remove_selected_by_index(idx_to_remove)
        except StopIteration:
            pass

    def _add_all_campaign_channels(self, campaign):
        count = 0
        for channel in campaign["channels"]:
            if not self._is_channel_in_list(channel["url"]):
                self.parent_app.config_data.add(channel["url"], self.parent_app.config_data.default_drop_minutes)
                count += 1

        self.parent_app.status_label.setText(
            self.t("drops_added").format(channel=f"{count} канал(ов)")
        )

    def _display_campaigns(self, campaigns, driver=None):
        if not campaigns:
            QMetaObject.invokeMethod(
                self.status_label,
                "setText",
                Qt.ConnectionType.QueuedConnection,
                Q_ARG(str, self.t("drops_no_campaigns_found"))
            )
            no_data_label = QLabel(self.t("drops_no_campaigns_found"))
            no_data_label.setObjectName("NoCampaignsLabel") # Устанавливаем objectName для применения стилей из QSS
            self.scroll_layout.addWidget(no_data_label)
            return

        QMetaObject.invokeMethod(
            self.status_label,
            "setText",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.t("drops_loaded").format(count=len(campaigns)))
        )

        games = {}
        for campaign in campaigns:
            if not isinstance(campaign, dict):
                print(f"Предупреждение: Пропущен элемент кампании, который не является словарем: {campaign}")
                continue
            game_name = campaign["game"]
            if game_name not in games:
                games[game_name] = {"campaigns": []}
            games[game_name]["campaigns"].append(campaign)

        for game_name, game_data in games.items():
            game_group = CollapsibleGroup(game_name, self.scroll_content)
            self.scroll_layout.addWidget(game_group)

            for campaign in game_data["campaigns"]:
                campaign_widget = QFrame()
                campaign_widget.setObjectName("CampaignFrame") # Устанавливаем objectName для стилей из QSS
                # campaign_widget.setFrameShape(QFrame.Shape.StyledPanel)
                # campaign_widget.setFrameShadow(QFrame.Shadow.Raised)
                # campaign_widget.setStyleSheet(
                #     "background-color: #2D2D2D; border-radius: 10px; margin-bottom: 10px; border: 1px solid #444444;"
                # )
                campaign_layout = QVBoxLayout(campaign_widget)
                campaign_layout.setContentsMargins(10, 8, 10, 8)

                # Campaign Header
                header = QWidget()
                header_layout = QHBoxLayout(header)
                header_layout.setContentsMargins(0, 0, 0, 0)

                name_label = QLabel(f"<b>{campaign['name']}</b>")
                name_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
                header_layout.addWidget(name_label)

                status_color = (
                    "#00B060" if campaign["status"] == "active" else "#FFA000"
                )
                status_label = QLabel(campaign["status"].upper())
                status_label.setStyleSheet(
                    f"padding: 3px 8px; border-radius: 6px; background-color: {status_color}; color: white; font-weight: bold;"
                )
                header_layout.addWidget(status_label)
                header_layout.addStretch(1)

                campaign_layout.addWidget(header)

                # Rewards
                rewards = campaign.get("rewards", [])
                if rewards:
                    rewards_frame = QFrame()
                    rewards_frame.setObjectName("RewardsFrame") # Устанавливаем objectName для стилей из QSS
                    # rewards_frame.setStyleSheet("background-color: #333333; border-radius: 8px; padding: 5px;")
                    rewards_layout = QHBoxLayout(rewards_frame)
                    rewards_layout.setContentsMargins(5, 5, 5, 5)
                    rewards_layout.addWidget(QLabel("🎁 Rewards:"))

                    for rew_idx, reward in enumerate(rewards[:6]):
                        reward_img_url = reward.get("image_url", "")
                        if reward_img_url and not reward_img_url.startswith("http"):
                            reward_img_url = f"https://ext.cdn.kick.com/{reward_img_url}"

                        if reward_img_url and driver:
                            reward_label = QLabel()
                            # Присваиваем уникальное objectName
                            reward_label.setObjectName(f"reward_image_{campaign['id']}_{rew_idx}")
                            reward_label.setFixedSize(50, 50) # Устанавливаем фиксированный размер для лейбла
                            reward_label.setScaledContents(True)
                            rewards_layout.addWidget(reward_label)
                            # Передаем objectName вместо объекта QLabel
                            threading.Thread(target=self._load_reward_image_async, args=(reward_img_url, reward_label.objectName()), daemon=True).start()
                    campaign_layout.addWidget(rewards_frame)

                # Channels
                channels_widget = QWidget()
                channels_layout = QVBoxLayout(channels_widget)
                channels_layout.setContentsMargins(0, 0, 0, 0)

                if not campaign["channels"]:
                    channels_layout.addWidget(QLabel(self.t("drops_no_channels")))
                else:
                    for channel in campaign["channels"][:5]:
                        channel_row = QWidget()
                        channel_row_layout = QHBoxLayout(channel_row)
                        channel_row_layout.setContentsMargins(0, 5, 0, 5)

                        ch_label = QLabel(
                            f'<a href="{channel["url"]}" style="color: #00B060; text-decoration: none;">{channel["username"]}</a>'
                        )
                        ch_label.linkActivated.connect(
                            lambda url: QDesktopServices.openUrl(QUrl(url))
                        )
                        channel_row_layout.addWidget(ch_label)
                        channel_row_layout.addStretch(1)

                        is_added = self._is_channel_in_list(channel["url"])
                        action_btn = QPushButton(
                            "✗ Удалить" if is_added else "+ Добавить"
                        )
                        action_btn.setFixedSize(120, 30)
                        action_btn.setObjectName("DropActionButton")

                        # Удаляем встроенные стили, так как они теперь в styles.qss
                        # action_btn.setStyleSheet(
                        #     f"""
                        #     QPushButton#DropActionButton {{
                        #         background-color: {'#B00020' if is_added else '#404040'};
                        #         border: none;
                        #         color: white;
                        #         border-radius: 8px;
                        #         padding: 5px;
                        #     }}
                        #     QPushButton#DropActionButton:hover {{
                        #         background-color: {'#800000' if is_added else '#505050'};
                        #     }}
                        # """
                        # )

                        def create_toggle_function(url, btn):
                            def toggle():
                                if self._is_channel_in_list(url):
                                    self._remove_drop_channel(url)
                                    btn.setText("""+ Добавить""")
                                    # Удаляем inline-стили
                                    btn.setStyleSheet("")
                                else:
                                    self._add_drop_channel(url)
                                    btn.setText("""✗ Удалить""")
                                    # Удаляем inline-стили
                                    btn.setStyleSheet("")
                            return toggle

                        action_btn.clicked.connect(
                            create_toggle_function(channel["url"], action_btn)
                        )

                        channel_row_layout.addWidget(action_btn)
                        channels_layout.addWidget(channel_row)

                    # Add All Button
                    add_all_btn = QPushButton(self.t("btn_add_all_channels"))
                    add_all_btn.setObjectName("AddAllButton")
                    # Удаляем встроенные стили, так как они теперь в styles.qss
                    # add_all_btn.setStyleSheet(
                    #     """
                    #     QPushButton#AddAllButton {
                    #         background-color: #008080;
                    #         border: none;
                    #         color: white;
                    #         padding: 10px;
                    #         border-radius: 12px;
                    #         margin-top: 10px;
                    #     }
                    #     QPushButton#AddAllButton:hover {
                    #         background-color: #009999;
                    #     }
                    # """
                    # )
                    add_all_btn.clicked.connect(
                        lambda checked, c=campaign: self._add_all_campaign_channels(c)
                    )
                    channels_layout.addWidget(add_all_btn)

                campaign_layout.addWidget(channels_widget)
                game_group.add_widget(campaign_widget)

    def closeEvent(self, event):
        self._is_closed = True
        super().closeEvent(event)
