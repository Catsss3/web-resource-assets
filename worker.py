#!/usr/bin/env python3
import base64, json, os, subprocess, sys, time, requests
from pathlib import Path
from typing import List, Dict, Optional
from urllib.parse import urlparse, parse_qs

# --------------------------- Конфигурация ---------------------------
CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = Path("./xray")
XRAY_DOWNLOAD_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip"
XRAY_ZIP = Path("xray.zip")
REQUEST_TIMEOUT = 5

ACTIVE_SNI_PATH = "lists/active_endpoints.txt"
INPUT_DIR_PATH = "input"
SUBSCRIPTION_PATH = "subscription.txt"

def log(msg: str, level: str = "INFO") -> None:
    print(f"[{level}] {msg}")

def install_xray() -> None:
    if XRAY_BIN.is_file(): return
    log("Скачиваю Xray...")
    cmd = f"curl -L -s {XRAY_DOWNLOAD_URL} -o {XRAY_ZIP} && unzip -o -q {XRAY_ZIP} && chmod +x {XRAY_BIN}"
    subprocess.run(cmd, shell=True, check=True)
    if XRAY_ZIP.is_file(): XRAY_ZIP.unlink()

def parse_vless(uri: str):
    parsed = urlparse(uri)
    user_id = parsed.netloc.split("@")[0]
    host_port = parsed.netloc.split("@")[1]
    address, port = host_port.split(":")
    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
    return user_id, address, int(port), params

def build_config(address, port, user_id, net_type, sni_mask, extra_params):
    return {
        "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "socks"}],
        "outbounds": [{
            "protocol": "vless",
            "settings": {"vnext": [{"address": address, "port": port, "users": [{"id": user_id, "encryption": "none"}]}]},
            "streamSettings": {
                "network": net_type, "security": "tls",
                "tlsSettings": {"serverName": sni_mask, "allowInsecure": True},
                "wsSettings": {"path": extra_params.get("path", "/")} if net_type == "ws" else None,
                "grpcSettings": {"serviceName": extra_params.get("serviceName", "")} if net_type == "grpc" else None,
            }
        }]
    }

def wait_port(port: int, timeout: float = 3.0) -> bool:
    import socket
    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0: return True
        time.sleep(0.1)
    return False

def test_vless(vless_link: str, sni_mask: str) -> bool:
    cfg_path = Path("config_tmp.json")
    try:
        uid, addr, port, params = parse_vless(vless_link)
        net = params.get("type", "tcp")
        cfg = build_config(addr, port, uid, net, sni_mask, params)
        cfg_path.write_text(json.dumps(cfg))
        with subprocess.Popen([str(XRAY_BIN), "-c", str(cfg_path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as proc:
            if not wait_port(10808): return False
            try:
                r = requests.get(CHECK_URL, proxies={"http": "socks5h://127.0.0.1:10808", "https": "socks5h://127.0.0.1:10808"}, timeout=REQUEST_TIMEOUT)
                return r.status_code == 204
            except: return False
            finally: proc.terminate()
    except: return False
    finally:
        if cfg_path.is_file(): cfg_path.unlink()

def push_file(path: str, content: str, msg: str, headers: dict) -> None:
    url = f"https://api.github.com/repos/{REPO}/contents/{path}"
    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None
    data = {"message": msg, "content": base64.b64encode(content.encode()).decode(), "sha": sha}
    requests.put(url, headers=headers, json=data)

def main():
    install_xray()
    token = os.getenv("WORKFLOW_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    if not token or not repo: sys.exit(1)
    global REPO
    REPO = repo
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    sni_list = ["google.com"]
    sni_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/{ACTIVE_SNI_PATH}", headers=headers)
    if sni_resp.status_code == 200:
        try:
            raw = sni_resp.json().get("content", "")
            decoded = base64.b64decode(raw).decode().split("\n")
            sni_list = [s.strip() for s in decoded if s.strip()]
        except: pass

    inp_resp = requests.get(f"https://api.github.com/repos/{repo}/contents/{INPUT_DIR_PATH}", headers=headers)
    if inp_resp.status_code != 200: return

    working_links = []
    for item in inp_resp.json():
        if item["type"] != "file" or item["name"].startswith("."): continue
        raw_url = item.get("download_url")
        if not raw_url: continue
        
        try:
            content = requests.get(raw_url).text
            for line in content.splitlines():
                if not line.strip().startswith("vless://"): continue
                for sni in sni_list:
                    if test_vless(line.strip(), sni):
                        base = line.strip().split("?")[0]
                        working_links.append(f"{base}?encryption=none&security=tls&sni={sni}#Blondie_Vip")
                        break
            requests.delete(item["url"], headers=headers, json={"message": "🧹 Clean input", "sha": item["sha"]})
        except: continue

    if working_links:
        push_file(SUBSCRIPTION_PATH, "\n".join(sorted(list(set(working_links)))), "🔥 Update Subscription", headers)

if __name__ == "__main__":
    main()
