import os, sys, base64, json, logging, time, requests
from urllib.parse import urlparse

# Настройки
REPO = os.getenv("GITHUB_REPOSITORY", "Catsss3/web-resource-assets")
TOKEN = os.getenv("WORKFLOW_TOKEN")
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

if not TOKEN:
    raise RuntimeError("❌ WORKFLOW_TOKEN не найден")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def _github_put(path: str, content: str, message: str) -> None:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    resp = requests.get(url, headers=HEADERS)
    sha = resp.json().get("sha") if resp.status_code == 200 else None
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": "main",
    }
    if sha: payload["sha"] = sha
    put_resp = requests.put(url, headers=HEADERS, json=payload)
    if put_resp.status_code not in (200, 201):
        raise RuntimeError(f"❌ Ошибка записи {path}: {put_resp.text}")

def _fetch_raw(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200: return r.text
    except: pass
    return None

def _extract_vless_links(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip().startswith("vless://")]

def collect() -> None:
    search_url = "https://api.github.com/search/code?q=vless://+in:file+language:yaml&per_page=100"
    logging.info("Запрос к GitHub Search API")
    try:
        r = requests.get(search_url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        items = r.json().get("items", [])
    except Exception as e:
        logging.error(f"Ошибка поиска: {e}"); return

    found_links: list[str] = []
    for item in items:
        raw_url = item["html_url"].replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
        content = _fetch_raw(raw_url)
        if content: found_links.extend(_extract_vless_links(content))

    if not found_links:
        logging.info("Новых ссылок не найдено"); return

    unique_links = list(dict.fromkeys(found_links))[:100]
    try:
        _github_put("input/fresh_raw_links.txt", "\n".join(unique_links), "📡 Blondie: New Scrape Success")
        logging.info(f"Сохранено {len(unique_links)} уникальных ссылок")
    except RuntimeError as e:
        logging.error(e)

if __name__ == "__main__":
    collect()
