import os
import json
import time

from loader.core.paths import COOKIES_DIR # Используем COOKIES_DIR из paths


class CookieManager:
    @staticmethod
    def domain_from_url(url):
        from urllib.parse import urlparse
        p = urlparse(url)
        return p.netloc

    @staticmethod
    def cookie_file_for_domain(domain):
        safe = domain.replace(":", "_")
        return os.path.join(COOKIES_DIR, f"{safe}.json")

    @staticmethod
    def save_cookies(driver, domain):
        path = CookieManager.cookie_file_for_domain(domain)
        cookies = driver.get_cookies()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
        return path

    @staticmethod
    def load_cookies(driver, domain):
        path = CookieManager.cookie_file_for_domain(domain)
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        for c in cookies:
            # Fix certain fields that cause problems
            if "expiry" in c and c["expiry"] is None:
                del c["expiry"]
            try:
                driver.add_cookie(c)
            except Exception:
                pass
        return True

    @staticmethod
    def import_from_browser(domain: str) -> bool:
        """Attempts to import existing cookies from browsers (Chrome/Edge/Firefox)
        using browser_cookie3. Returns True if a file was written.
        """
        try:
            import browser_cookie3 as bc3  # type: ignore
        except Exception:
            return False

        try:
            cj = bc3.load(domain_name=domain)
        except Exception:
            cj = None

        if not cj:
            return False

        cookies = []
        try:
            for c in cj:
                if not getattr(c, "name", None):
                    continue
                cookie = {
                    "name": c.name,
                    "value": c.value,
                    "domain": getattr(c, "domain", domain) or domain,
                    "path": getattr(c, "path", "/") or "/",
                    "secure": bool(getattr(c, "secure", False)),
                }
                exp = getattr(c, "expires", None)
                if exp is not None:
                    try:
                        cookie["expiry"] = int(exp)
                    except Exception:
                        pass
                cookies.append(cookie)
        except Exception:
            return False

        if not cookies:
            return False

        path = CookieManager.cookie_file_for_domain(domain)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2)
            return True
        except Exception:
            return False

    @staticmethod
    def delete_cookies(domain: str) -> bool:
        """Удаляет файл куки для указанного домена."""
        path = CookieManager.cookie_file_for_domain(domain)
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"Файл куки для домена {domain} удален: {path}")
                return True
            except Exception as e:
                print(f"Ошибка при удалении файла куки для {domain}: {e}")
                return False
        else:
            print(f"Файл куки для домена {domain} не найден: {path}")
            return False

    @staticmethod
    def check_cookies(domain: str) -> bool:
        """Проверяет наличие действительных куки для указанного домена."""
        path = CookieManager.cookie_file_for_domain(domain)
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
        except json.JSONDecodeError:
            return False

        current_time = int(time.time())
        valid_cookies = [
            c for c in cookies if c.get("expiry", float('inf')) == -1 or c.get("expiry", float('inf')) > current_time
        ]
        return bool(valid_cookies)
