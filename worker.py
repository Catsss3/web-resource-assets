
import os, requests, base64, re

TOKEN = os.getenv('WORKFLOW_TOKEN')
REPO = os.getenv('GITHUB_REPOSITORY')
HEADERS = {"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github.v3+json"}

def run():
    print("👠 Блонди вошла в чат...")
    res = requests.get(f"https://api.github.com/repos/{REPO}/contents/input", headers=HEADERS)
    if res.status_code != 200: return

    files = res.json()
    if not isinstance(files, list): return

    valid_nodes = []
    files_to_del = []

    for f in files:
        if f['name'].startswith('.'): continue
        print(f"📦 Читаю: {f['name']}")
        content = requests.get(f['download_url']).text
        for line in content.split('\n'):
            if "://" in line:
                # Маскируем под Госуслуги
                masked = re.sub(r'(sni=)[^&#]+', r'\1v01.gosuslugi.ru', line.strip())
                valid_nodes.append(masked)
        files_to_del.append(f)

    if valid_nodes:
        # Сохраняем в подписку
        sub_url = f"https://api.github.com/repos/{REPO}/contents/subscription.txt"
        r_sub = requests.get(sub_url, headers=HEADERS)
        sha = r_sub.json()['sha'] if r_sub.status_code == 200 else None
        
        final_text = "\n".join(list(set(valid_nodes)))
        requests.put(sub_url, headers=HEADERS, json={
            "message": "💎 Updated by Worker",
            "content": base64.b64encode(final_text.encode()).decode(),
            "sha": sha
        })
        
        # Чистим input
        for f in files_to_del:
            requests.delete(f"https://api.github.com/repos/{REPO}/contents/{f['path']}", 
                            headers=HEADERS, json={"message": "Cleaned! 💋", "sha": f['sha']})
        print("✅ Всё готово, подписка обновлена!")

if __name__ == "__main__":
    run()
