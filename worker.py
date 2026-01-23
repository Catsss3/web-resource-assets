#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from urllib.parse import parse_qs, urlparse

# --------------------------- Константы --------------------------- #
CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = Path("./xray")
XRAY_DOWNLOAD_URL = (
    "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
)
XRAY_ZIP = Path("xray.zip")
REQUEST_TIMEOUT = 5  # seconds
SLEEP_FOR_XRAY = 1.5   # fallback pause while waiting for Xray to bind

# --------------------------- Логирование --------------------------- #
def log(msg: str, level: str = "INFO") -> None:
    print(f"[{level}] {msg}", file=sys.stderr if level == "ERROR" else sys.stdout)

# --------------------------- Утилиты --------------------------- #
def install_xray() -> None:
    if XRAY_BIN.is_file():
        log("Xray уже установлен.")
        return
    log("Скачиваю Xray...")
    cmd = (
        f"curl -L -s {XRAY_DOWNLOAD_URL} -o {XRAY_ZIP} && "
        f"unzip -o -q {XRAY_ZIP} && "
        f"chmod +x {XRAY_BIN}"
    )
    subprocess.run(cmd, shell=True, check=True)
    XRAY_ZIP.unlink(missing_ok=True)
    log("Xray успешно установлен.")

def parse_vless(uri: str) -> Tuple[str, str, int, Dict[str, str]]:
    parsed = urlparse(uri)
    if parsed.scheme != "vless":
        raise ValueError("Не VLESS‑ссылка")
    user_id = parsed.netloc.split("@")[0]
    host_port = parsed.netloc.split("@")[1]
    address, port_str = host_port.split(":")
    port = int(port_str)
    raw_params = parse_qs(parsed.query)
    params = {k: v[0] for k, v in raw_params.items()}
    return user_id, address, port, params

def build_config(address, port, user_id, net_type, sni_mask, extra_params) -> Dict:
    ws_path = extra_params.get("path", "/")
    grpc_service = extra_params.get("serviceName", "")
    stream_settings = {
        "network": net_type,
        "security": "tls",
        "tlsSettings": {"serverName": sni_mask, "allowInsecure": True},
    }
    if net_type == "ws":
        stream_settings["wsSettings"] = {"path": ws_path}
    elif net_type == "grpc":
        stream_settings["grpcSettings"] = {"serviceName": grpc_service}
    return {
        "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "socks"}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": address, "port": port, "users": [{"id": user_id, "encryption": "none"}]}]},
            "streamSettings": stream_settings,
        }],
    }

def wait_port(host: str, port: int, timeout: float = 3.0) -> bool:
    import socket
    end = time.time() + timeout
    while time.time() < end:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.connect((host, port))
                return True
            except OSError:
                time.sleep(0.1)
    return False

def test_vless(vless_link: str, sni_mask: str) -> bool:
    cfg_path = Path("config_tmp.json")
    try:
        user_id, address, port, params = parse_vless(vless_link)
        net_type = params.get("type", "tcp")
        config = build_config(address, port, user_id, net_type, sni_mask, params)
        cfg_path.write_text(json.dumps(config, ensure_ascii=False))
        with subprocess.Popen([str(XRAY_BIN), "-c", str(cfg_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as proc:
            if not wait_port("127.0.0.1", 10808): return False
            try:
                resp = requests.get(CHECK_URL, proxies={"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}, timeout=REQUEST_TIMEOUT)
                return resp.status_code == 204
            except: return False
            finally: proc.terminate()
    except Exception as exc:
        log(f"Ошибка: {exc}", "ERROR")
        return False
    finally:
        if cfg_path.is_file(): cfg_path.unlink(missing_ok=True)

def main():
    install_xray()
    token = os.getenv('WORKFLOW_TOKEN')
    repo = os.getenv('GITHUB_REPOSITORY')
    h = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
    
    # SNI берем из папки lists
    sni_res = requests.get(f"https://api.github.com/repos/{repo}/contents/lists/active_endpoints.txt", headers=h).json()
    sni_list = base64.b64decode(sni_res['content']).decode().split('\n')
    sni_list = [s.strip() for s in sni_list if s.strip()]

    # Читаем input
    inp_res = requests.get(f"https://api.github.com/repos/{repo}/contents/input", headers=h)
    if inp_res.status_code != 200: return
    
    working_masked_links = []
    for item in inp_res.json():
        if item["name"] == ".keep": continue
        raw_content = requests.get(item["download_url"]).text
        for line in raw_content.split('\n'):
            line = line.strip()
            if not line.startswith("vless://"): continue
            for sni in sni_list:
                if test_vless(line, sni):
                    base = line.split("?")[0]
                    working_masked_links.append(f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Blondie_Vip")
        # Удаляем обработанный файл
        requests.delete(item["url"], headers=h, json={"message": "🧹 Clean input", "sha": item["sha"]})

    if working_masked_links:
        sub_url = f"https://api.github.com/repos/{repo}/contents/subscription.txt"
        sha = requests.get(sub_url, headers=h).json().get("sha")
        final_txt = "\n".join(sorted(set(working_masked_links)))
        requests.put(sub_url, headers=h, json={"message": "🔥 Verified Nodes", "content": base64.b64encode(final_txt.encode()).decode(), "sha": sha})

if __name__ == "__main__":
    main()
