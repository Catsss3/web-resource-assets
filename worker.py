import os, re, base64, requests

TOKEN = os.getenv('WORKFLOW_TOKEN')
REPO = os.getenv('GITHUB_REPOSITORY')
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_file_sha(path: str):
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS)
    return r.json().get('sha') if r.status_code == 200 else None

def get_file_content(path: str) -> str:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200: return ""
    return base64.b64decode(r.json()['content']).decode()

def push_content(path: str, content: str, message: str):
    sha = get_file_sha(path)
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode()
    }
    if sha: payload["sha"] = sha
    requests.put(url, headers=HEADERS, json=payload)

def main():
    print("👠 Блонди вошла в чат... Начинаю радикальный подбор!")
    sni_raw = get_file_content("endpoints.txt")
    sni_list = [s.strip() for s in sni_raw.split("\n") if s.strip()]

    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/input", headers=HEADERS)
    if r.status_code != 200: return
    items = r.json()

    valid_links = []
    files_to_delete = []

    for item in items:
        if item["name"] == ".keep": continue
        files_to_delete.append(item)
        raw = requests.get(item["download_url"]).text
        for line in raw.split("\n"):
            if "://" not in line: continue
            for sni in sni_list:
                masked = re.sub(r"(sni=)[^&#]+", r"\1" + sni, line.strip())
                valid_links.append(masked)

    if valid_links:
        uniq_list = sorted(list(set(valid_links)))
        count = len(uniq_list)
        final_data = "\n".join(uniq_list)
        push_content("subscription.txt", final_data, f"✅ Workers: Added {count} proxies")
        print(f"🔥 Успех! Добавлено много новых узлов.")

    for f in files_to_delete:
        requests.delete(f"https://api.github.com/repos/{REPO}/contents/{f['path']}", 
                        headers=HEADERS, json={"message": "🗑 Clean input", "sha": f["sha"]})
    print("🧹 Входная папка очищена.")

if __name__ == "__main__":
    main()
