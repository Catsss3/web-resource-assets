#!/usr/bin/env python3
import base64, json, os, random, subprocess, sys, time, tempfile, requests
from pathlib import Path
from urllib.parse import urlparse, parse_qs

XRAY_BIN = Path("./xray")
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
CHECK_URLS = ["https://www.google.com/generate_204", "https://1.1.1.1/generate_204"]

def log(msg, level="INFO"): print(f"[{level}] {msg}")

def install_xray():
    if XRAY_BIN.is_file(): return
    log("Начинаю установку Xray...")
    try:
        subprocess.run("sudo apt-get update -y && sudo apt-get install -y unzip curl", shell=True, check=True, stdout=subprocess.DEVNULL)
        subprocess.run(f"curl -L -s {XRAY_URL} -o xray.zip && unzip -o xray.zip && chmod +x xray", shell=True, check=True)
        ver = subprocess.check_output("./xray version", shell=True).decode().splitlines()[0]
        log(f"Xray готов: {ver}")
    except Exception as e: log(f"Ошибка установки: {e}", "ERROR"); sys.exit(1)

def test_vless(link_data, sni):
    security = link_data["params"].get("security", "tls")
    network = link_data["params"].get("type", "tcp")
    config = {
        "log": {"loglevel": "none"},
        "inbounds": [{"port": 10808, "protocol": "socks", "settings": {"auth": "noauth"}, "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": link_data["addr"], "port": link_data["port"], "users": [{"id": link_data["uuid"], "encryption": "none"}]}]},
            "streamSettings": {
                "network": network, "security": security,
                "tlsSettings": {"serverName": sni, "allowInsecure": True} if security == "tls" else None,
                "realitySettings": {"serverName": sni, "publicKey": link_data["params"].get("pbk"), "shortId": link_data["params"].get("sid", ""), "spiderX": link_data["params"].get("spx", "/")} if security == "reality" else None,
                "wsSettings": {"path": link_data["params"].get("path", "/")} if network == "ws" else None,
                "httpSettings": {"path": link_data["params"].get("path", "/"), "host": [sni]} if network == "http" else None,
            }
        }]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(config, tmp); cfg_path = tmp.name
    proc = subprocess.Popen([str(XRAY_BIN), "run", "-c", cfg_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    ok = False
    try:
        r = requests.get(CHECK_URLS[0], proxies={"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}, timeout=12)
        if r.status_code in (200, 204): ok = True
    except: pass
    finally:
        proc.terminate(); proc.wait()
        if os.path.exists(cfg_path): os.remove(cfg_path)
    return ok

def main():
    install_xray()
    # Берем токен из секретов гитхаба
    token = os.getenv("WORKFLOW_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not token or not repo: return

    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    log("Загружаю SNI...")
    sni_list = ["google.com"]
    sni_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/lists/active_endpoints.txt", headers=headers)
    if sni_resp.status_code == 200:
        sni_list = [s.strip() for s in base64.b64decode(sni_resp.json()["content"]).decode().splitlines() if s.strip()]

    log("Сканирую склад (input)...")
    inp_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/input", headers=headers)
    if inp_resp.status_code != 200: return

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
                if "@" in netloc:
                    user_part, host_part = netloc.split("@", 1)
                else:
                    decoded = base64.urlsafe_b64decode(netloc + "==").decode()
                    user_part, host_part = decoded.split("@")
                
                addr, port = host_part.split(":")
                data = {"uuid": user_part, "addr": addr, "port": int(port), "params": {k: v[0] for k, v in parse_qs(parsed.query).items()}}

                random.shuffle(sni_list)
                for sni in sni_list[:3]:
                    if test_vless(data, sni):
                        log(f"✅ Рабочая! SNI: {sni}")
                        base = link.split("?")[0]
                        valid_links.append(f"{base}?{parsed.query}&sni={sni}#Blondie_Vip")
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

if __name__ == "__main__":
    main()
