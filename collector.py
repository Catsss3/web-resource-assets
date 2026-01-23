import os, sys, base64, json, logging, time, requests

# 1️⃣ Настройка логирования
logging.basicConfig(
    filename="collector.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

def log_info(msg: str) -> None:
    print(msg)
    logging.info(msg)

def log_error(msg: str) -> None:
    print(f"❌ {msg}")
    logging.error(msg)

# 2️⃣ Конфигурация
WORKFLOW_TOKEN = os.getenv("WORKFLOW_TOKEN")
GITHUB_TOKEN   = os.getenv("GITHUB_TOKEN")
REPO           = os.getenv("GITHUB_REPOSITORY", "Catsss3/web-resource-assets")

TOKEN = WORKFLOW_TOKEN or GITHUB_TOKEN
if not TOKEN:
    log_error("Токен WORKFLOW_TOKEN/GITHUB_TOKEN не найден")
    sys.exit(1)

HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "Blondie-Smart-Collector/2.0",
}

# 3️⃣ Работа с файлом sources.txt
def load_sources(path: str = "sources.txt") -> list[str]:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code == 200:
        content = base64.b64decode(resp.json()["content"]).decode()
        return [line.strip() for line in content.splitlines() if line.strip()]
    return []

def save_sources(sources: list[str], path: str = "sources.txt") -> None:
    content = "\n".join(sources) + "\n"
    push_file(path, content, "📡 Blondie: Update sources list")

# 4️⃣ Поиск новых источников на GitHub
def discover_new_sources(existing: set[str]) -> set[str]:
    log_info("🔎 Поиск новых источников на GitHub...")
    new_found = set()
    search_url = "https://api.github.com/search/code"
    params = {
        "q": "vless:// in:file language:yaml",
        "per_page": 30,
        "page": 1,
    }
    try:
        resp = requests.get(search_url, headers=HEADERS, params=params, timeout=15)
        resp.raise_for_status()
        items = resp.json().get("items", [])
        for item in items:
            raw_url = (
                item["html_url"]
                .replace("github.com", "raw.githubusercontent.com")
                .replace("/blob/", "/")
            )
            if raw_url not in existing:
                new_found.add(raw_url)
    except Exception as e:
        log_error(f"Ошибка при поиске: {e}")
    return new_found

# 5️⃣ Валидация VLESS‑ссылок
def is_valid_vless(link: str) -> bool:
    if not link.startswith("vless://"):
        return False
    low = link.lower()
    return ("security=tls" in low) or ("reality" in low)

# 6️⃣ Запись файлов в репозиторий
def push_file(path: str, content: str, msg: str) -> None:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    resp = requests.get(url, headers=HEADERS, timeout=10)
    sha = resp.json().get("sha") if resp.status_code == 200 else None
    data = {
        "message": msg,
        "content": base64.b64encode(content.encode()).decode(),
        "sha": sha,
    }
    put_resp = requests.put(url, headers=HEADERS, json=data, timeout=10)
    if put_resp.status_code in (200, 201):
        log_info(f"✅ {msg}")
    else:
        log_error(f"❌ Ошибка {put_resp.status_code}: {put_resp.text}")

# 7️⃣ Основная логика сбора
def collect() -> None:
    current_sources = set(load_sources())
    log_info(f"📂 Загружено {len(current_sources)} источников")
    new_sources = discover_new_sources(current_sources)
    if new_sources:
        updated = sorted(current_sources.union(new_sources))
        save_sources(updated)
        current_sources = set(updated)
        log_info(f"🔎 Добавлено {len(new_sources)} новых источников")
    else:
        log_info("🔎 Новых источников не найдено")
    found_links = []
    for url in current_sources:
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                for line in resp.text.splitlines():
                    line = line.strip()
                    if is_valid_vless(line):
                        found_links.append(line)
        except Exception as e:
            log_error(f"Ошибка при запросе {url}: {e}")
    if not found_links:
        log_info("⚠️ Не найдено ни одной подходящей ссылки")
        return
    unique_links = list(dict.fromkeys(found_links))[:100]
    final_content = "\n".join(unique_links) + "\n"
    push_file("input/fresh_raw_links.txt", final_content, "📡 Blondie: Daily Scrape Results")
    log_info(f"✅ Сохранено {len(unique_links)} ссылок")

if __name__ == "__main__":
    collect()
