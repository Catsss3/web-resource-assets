#!/usr/bin/env python3
import base64
import json
import os
import subprocess
import sys
import time
import requests
import tempfile
import random
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# -------------------- Конфигурация --------------------
CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = Path("./xray")
XRAY_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"

def log(msg: str, level: str = "INFO") -> None:
    print(f"[{level}] {msg}")

def run_cmd(cmd: str) -> None:
    subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def install_xray() -> None:
    if XRAY_BIN.is_file():
        log("Xray уже установлен.")
        return
    log("Начинаю установку Xray...")
    try:
        run_cmd("sudo apt-get update -y && sudo apt-get install -y unzip curl")
        run_cmd(f"curl -L -s {XRAY_URL} -o xray.zip && unzip -o xray.zip && chmod +x xray")
        log("Xray успешно установлен.")
    except Exception as e:
        log(f"Ошибка установки Xray: {e}", "ERROR")
        sys.exit(1)

def test_vless(link_data: dict, sni: str) -> bool:
    config = {
        "inbounds": [{"port": 10808, "protocol": "socks", "settings": {"auth": "noauth"}}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {
                "vnext": [{"address": link_data["addr"], "port": link_data["port"], "users": [{"id": link_data["uuid"], "encryption": "none"}]}]
            },
            "streamSettings": {
                "network": link_data["params"].get("type", "tcp"),
                "security": "tls",
                "tlsSettings": {"serverName": sni, "allowInsecure": True},
                "wsSettings": ({"path": link_data["params"].get("path", "/")} if link_data["params"].get("type") == "ws" else None),
            }
        }]
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(config, tmp)
        tmp_path = tmp.name

    proc = subprocess.Popen([str(XRAY_BIN), "-c", tmp_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.5)
    success = False
    try:
        r = requests.get(CHECK_URL, proxies={"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}, timeout=5)
        if r.status_code == 204: success = True
    except: pass
    finally:
        proc.terminate()
        proc.wait()
        if os.path.exists(tmp_path): os.remove(tmp_path)
    return success

def main() -> None:
    install_xray()
    token = os.getenv("WORKFLOW_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not token or not repo: return
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    log("Загружаю список SNI...")
    sni_list = ["google.com"]
    sni_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/lists/active_endpoints.txt", headers=headers)
    if sni_resp.status_code == 200:
        sni_list = base64.b64decode(sni_resp.json()["content"]).decode().splitlines()
        sni_list = [s.strip() for s in sni_list if s.strip()]

    log("Проверяю папку input...")
    input_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/input", headers=headers)
    if input_resp.status_code != 200: return

    valid_links = []
    for file_meta in input_resp.json():
        if file_meta["name"].startswith("."): continue
        log(f"Обрабатываю файл: {file_meta['name']}")
        raw = requests.get(file_meta["download_url"]).text.splitlines()

        for link in raw:
            try:
                parsed = urlparse(link.strip())
                params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                if "@" in parsed.netloc: userinfo, hostport = parsed.netloc.split("@", 1)
                else: userinfo, hostport = parsed.username or "", parsed.netloc
                addr, port_str = hostport.split(":")
                data = {"uuid": userinfo, "addr": addr, "port": int(port_str), "params": params}

                # ПЕРЕМЕШИВАЕМ SNI ДЛЯ КАЖДОЙ ССЫЛКИ
                random.shuffle(sni_list)
                for sni in sni_list:
                    if test_vless(data, sni):
                        log(f"✅ Рабочая ссылка найдена (SNI: {sni})")
                        cleaned = link.strip().split("?")[0]
                        valid_links.append(f"{cleaned}?encryption=none&security=tls&sni={sni}#Blondie_Vip")
                        break
            except: continue
        requests.delete(file_meta["url"], headers=headers, json={"message": "🧹 Clean", "sha": file_meta["sha"]})

    if valid_links:
        sub_url = f"https://api.github.com/repos/{repo}/contents/subscription.txt"
        sub_get = requests.get(sub_url, headers=headers)
        sha = sub_get.json().get("sha") if sub_get.status_code == 200 else None
        content_b64 = base64.b64encode("\n".join(valid_links).encode()).decode()
        requests.put(sub_url, headers=headers, json={"message": "💄 Blondie: Auto-Update 💅", "content": content_b64, "sha": sha})
        log(f"🏆 Сохранено {len(valid_links)} рабочих ссылок.")

if __name__ == "__main__":
    main()
