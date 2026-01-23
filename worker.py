#!/usr/bin/env python3
import base64, json, os, subprocess, sys, time, requests, tempfile, random
from pathlib import Path
from urllib.parse import urlparse, parse_qs

CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = Path("./xray")
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"

def log(msg, level="INFO"): print(f"[{level}] {msg}")

def install_xray():
    if XRAY_BIN.is_file(): return
    log("Начинаю установку Xray...")
    subprocess.run("sudo apt-get update -y && sudo apt-get install -y unzip curl", shell=True, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(f"curl -L -s {XRAY_URL} -o xray.zip && unzip -o xray.zip && chmod +x xray", shell=True, check=True)
    log("Xray успешно установлен.")

def test_vless(link_data, sni):
    config = {
        "inbounds": [{"port": 10808, "protocol": "socks", "settings": {"auth": "noauth"}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": link_data["addr"], "port": link_data["port"], "users": [{"id": link_data["uuid"], "encryption": "none"}]}]},
            "streamSettings": {
                "network": link_data["params"].get("type", "tcp"),
                "security": "tls",
                "tlsSettings": {"serverName": sni, "allowInsecure": True},
                "wsSettings": ({"path": link_data["params"].get("path", "/")} if link_data["params"].get("type") == "ws" else None),
            }
        }]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(config, tmp)
        t_path = tmp.name
    p = subprocess.Popen([str(XRAY_BIN), "-c", t_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    ok = False
    try:
        r = requests.get(CHECK_URL, proxies={"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}, timeout=5)
        if r.status_code == 204: ok = True
    except: pass
    finally:
        p.terminate()
        p.wait()
        if os.path.exists(t_path): os.remove(t_path)
    return ok

def main():
    install_xray()
    
    # ПРЯМАЯ ПРОВЕРКА ПЕРЕМЕННЫХ
    token = os.getenv("WORKFLOW_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    
    if not token: log("ОШИБКА: WORKFLOW_TOKEN не найден!", "ERROR"); return
    if not repo: log("ОШИБКА: GITHUB_REPOSITORY не найден!", "ERROR"); return
    
    log(f"Работаю с репозиторием: {repo}")
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    log("Загружаю SNI...")
    sni_list = ["google.com"]
    r = requests.get(f"https://api.github.com/repos/{repo}/contents/lists/active_endpoints.txt", headers=headers)
    if r.status_code == 200:
        sni_list = base64.b64decode(r.json()["content"]).decode().splitlines()
        sni_list = [s.strip() for s in sni_list if s.strip()]
    log(f"Загружено {len(sni_list)} SNI.")

    log("Сканирую папку input...")
    res = requests.get(f"https://api.github.com/repos/{repo}/contents/input", headers=headers)
    if res.status_code != 200:
        log(f"Папка input недоступна (HTTP {res.status_code})", "ERROR"); return
    
    items = res.json()
    log(f"Нашел {len(items)} файлов в input.")

    valid_links = []
    for item in items:
        if item["name"].startswith("."): continue
        log(f">>> ОБРАБАТЫВАЮ: {item['name']}")
        
        raw_text = requests.get(item["download_url"]).text
        links = raw_text.splitlines()
        log(f"В файле {len(links)} ссылок.")

        for l in links:
            l = l.strip()
            if not l: continue
            try:
                p = urlparse(l)
                if "@" in p.netloc: u, hp = p.netloc.split("@", 1)
                else: u, hp = p.username or "", p.netloc
                a, prt = hp.split(":")
                d = {"uuid": u, "addr": a, "port": int(prt), "params": {k: v[0] for k, v in parse_qs(p.query).items()}}
                
                random.shuffle(sni_list)
                for s in sni_list:
                    if test_vless(d, s):
                        log(f"   ✅ OK! SNI: {s}")
                        valid_links.append(f"{l.split('?')[0]}?encryption=none&security=tls&sni={s}#Blondie_Vip")
                        break
            except: continue
        
        log(f"Удаляю файл {item['name']}...")
        requests.delete(item["url"], headers=headers, json={"message": "🧹 Clean", "sha": item["sha"]})

    if valid_links:
        log(f"Обновляю subscription.txt ({len(valid_links)} шт.)...")
        s_url = f"https://api.github.com/repos/{repo}/contents/subscription.txt"
        s_get = requests.get(s_url, headers=headers)
        sha = s_get.json().get("sha") if s_get.status_code == 200 else None
        requests.put(s_url, headers=headers, json={"message": "💄 Blondie: Auto-Update 💅", "content": base64.b64encode("\n".join(valid_links).encode()).decode(), "sha": sha})
        log("🏆 ВСЁ ГОТОВО!")
    else:
        log("Ни одной рабочей ссылки не найдено. 😢")

if __name__ == "__main__":
    main()
