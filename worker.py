#!/usr/bin/env python3
import base64, json, os, subprocess, sys, time, requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# --- Настройки ---
CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = Path("./xray")
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
SOCKS_PORT = 10808

def log(msg, level="INFO"): print(f"[{level}] {msg}")

def install_xray():
    if XRAY_BIN.is_file(): return
    log("Начинаю установку Xray...")
    try:
        # Тихая установка зависимостей и Xray
        subprocess.run("sudo apt-get update -y && sudo apt-get install -y unzip curl", shell=True, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(f"curl -L -s {XRAY_URL} -o xray.zip && unzip -o xray.zip && chmod +x xray", shell=True, check=True)
        log("Xray успешно установлен.")
    except Exception as e:
        log(f"Ошибка установки: {e}", "ERROR"); sys.exit(1)

def parse_vless(link):
    try:
        parsed = urlparse(link)
        params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
        user_info = parsed.netloc.split('@')
        uuid = user_info[0]
        addr_port = user_info[1].split(':')
        return {"uuid": uuid, "addr": addr_port[0], "port": int(addr_port[1]), "params": params}
    except: return None

def test_vless(link_data, sni):
    config = {
        "inbounds": [{"port": SOCKS_PORT, "protocol": "socks", "settings": {"auth": "noauth"}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": link_data['addr'], "port": link_data['port'], "users": [{"id": link_data['uuid'], "encryption": "none"}]}]},
            "streamSettings": {
                "network": link_data['params'].get('type', 'tcp'),
                "security": "tls",
                "tlsSettings": {"serverName": sni, "allowInsecure": True},
                "wsSettings": {"path": link_data['params'].get('path', '/')} if link_data['params'].get('type') == 'ws' else None
            }
        }]
    }
    
    with open("config_tmp.json", "w") as f: json.dump(config, f)
    
    # Запускаем Xray фоном
    proc = subprocess.Popen([str(XRAY_BIN), "-c", "config_tmp.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5) # Даем время на запуск
    
    success = False
    try:
        proxies = {"http": f"socks5h://127.0.0.1:{SOCKS_PORT}", "https": f"socks5h://127.0.0.1:{SOCKS_PORT}"}
        r = requests.get(CHECK_URL, proxies=proxies, timeout=5)
        if r.status_code == 204: success = True
    except: pass
    finally:
        proc.terminate()
        if os.path.exists("config_tmp.json"): os.remove("config_tmp.json")
    return success

def main():
    install_xray()
    token = os.getenv("WORKFLOW_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    h = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    # 1. Грузим SNI
    sni_list = ["google.com"]
    r = requests.get(f"https://api.github.com/repos/{repo}/contents/lists/active_endpoints.txt", headers=h)
    if r.status_code == 200:
        sni_list = base64.b64decode(r.json()['content']).decode().splitlines()
    
    # 2. Обработка input
    r = requests.get(f"https://api.github.com/repos/{repo}/contents/input", headers=h)
    if r.status_code != 200: return
    
    valid_links = []
    for file in r.json():
        if file['name'].startswith('.'): continue
        raw_links = requests.get(file['download_url']).text.splitlines()
        
        for link in raw_links:
            data = parse_vless(link.strip())
            if not data: continue
            for sni in sni_list:
                if test_vless(data, sni.strip()):
                    log(f"✅ Нашел рабочий! SNI: {sni.strip()}")
                    valid_links.append(f"{link.strip().split('?')[0]}?encryption=none&security=tls&sni={sni.strip()}#Blondie_Vip")
                    break
        
        # Удаляем отработанный файл
        requests.delete(file['url'], headers=h, json={"message": "🧹 Clean", "sha": file['sha']})

    # 3. Сохраняем результат
    if valid_links:
        sub_url = f"https://api.github.com/repos/{repo}/contents/subscription.txt"
        r_sub = requests.get(sub_url, headers=h)
        sha = r_sub.json().get('sha') if r_sub.status_code == 200 else None
        content = base64.b64encode("\n".join(valid_links).encode()).decode()
        requests.put(sub_url, headers=h, json={"message": "💎 Update Sub", "content": content, "sha": sha})

if __name__ == "__main__":
    main()
