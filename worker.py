#!/usr/bin/env python3
import base64, json, os, random, subprocess, sys, time, tempfile, requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# --- Конфигурация ---
XRAY_BIN = Path("./xray")
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
CHECK_URLS = ["https://www.gstatic.com/generate_204", "https://1.1.1.1/generate_204"]

def log(msg, level="INFO"): print(f"[{level}] {msg}")

def install_xray():
    if XRAY_BIN.is_file(): return
    log("Начинаю установку Xray...")
    try:
        subprocess.run("sudo apt-get update -y && sudo apt-get install -y unzip curl", shell=True, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(f"curl -L -s {XRAY_URL} -o xray.zip && unzip -o xray.zip && chmod +x xray", shell=True, check=True)
        # Проверка версии
        ver = subprocess.check_output("./xray -version", shell=True).decode().splitlines()[0]
        log(f"Xray установлен: {ver}")
    except Exception as e:
        log(f"Ошибка установки: {e}", "ERROR"); sys.exit(1)

def test_vless(link_data, sni):
    config = {
        "log": {"loglevel": "none"},
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
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(config, tmp); cfg_path = tmp.name

    proc = subprocess.Popen([str(XRAY_BIN), "-c", cfg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    ok = False
    proxies = {"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}
    try:
        for target in CHECK_URLS:
            try:
                r = requests.get(target, proxies=proxies, timeout=10)
                if r.status_code in (200, 204):
                    ok = True; break
            except: continue
    finally:
        proc.terminate(); proc.wait()
        if os.path.exists(cfg_path): os.remove(cfg_path)
    return ok

def main():
    install_xray()
    token, repo = os.getenv("WORKFLOW_TOKEN"), os.getenv("GITHUB_REPOSITORY")
    if not token or not repo:
        log("Ошибка: Переменные окружения не найдены!", "ERROR"); return

    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    # ПРОВЕРКА ПОДКЛЮЧЕНИЯ К API
    try:
        requests.get("https://api.github.com", timeout=5).raise_for_status()
        log("Подключение к API GitHub подтверждено.")
    except Exception as e:
        log(f"API недоступно: {e}", "ERROR"); return

    log("Загружаю SNI...")
    sni_list = ["google.com"]
    sni_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/lists/active_endpoints.txt", headers=headers)
    if sni_resp.status_code == 200:
        sni_list = [s.strip() for s in base64.b64decode(sni_resp.json()["content"]).decode().splitlines() if s.strip()]

    log("Сканирую склад (input)...")
    inp_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/input", headers=headers)
    if inp_resp.status_code != 200:
        log("Склад пуст или недоступен."); return

    valid_links = []
    for item in inp_resp.json():
        if item["name"].startswith("."): continue
        log(f"Обрабатываю: {item['name']}")
        raw = requests.get(item["download_url"]).text.splitlines()

        for raw_link in raw:
            link = raw_link.strip()
            if not link or "vless://" not in link: continue
            try:
                parsed = urlparse(link)
                netloc = parsed.netloc
                if "@" in netloc: user_part, host_part = netloc.split("@", 1)
                else: user_part, host_part = parsed.username or "", netloc
                
                addr, port_str = host_part.split(":")
                data = {"uuid": user_part, "addr": addr, "port": int(port_str), "params": {k: v[0] for k, v in parse_qs(parsed.query).items()}}

                random.shuffle(sni_list)
                for sni in sni_list[:5]: # Проверяем топ-5
                    if test_vless(data, sni):
                        log(f"✅ Рабочая! SNI: {sni}")
                        base = link.split("?")[0]
                        valid_links.append(f"{base}?encryption=none&security=tls&sni={sni}#Blondie_Vip")
                        break
            except: continue

        requests.delete(item["url"], headers=headers, json={"message": "🧹 Clean", "sha": item["sha"]})

    if valid_links:
        sub_url = f"https://api.github.com/repos/{repo}/contents/subscription.txt"
        sub_resp = requests.get(sub_url, headers=headers)
        sha = sub_resp.json().get("sha") if sub_resp.status_code == 200 else None
        
        content_b64 = base64.b64encode("\n".join(valid_links).encode()).decode()
        requests.put(sub_url, headers=headers, json={"message": "💄 Blondie: High-Quality Update 💅", "content": content_b64, "sha": sha})
        log(f"🏆 Успех! Сохранено {len(valid_links)} ссылок.")
    else: log("Рабочих ссылок не найдено. 😢", "WARN")

if __name__ == "__main__":
    main()
