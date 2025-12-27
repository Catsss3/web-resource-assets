import os, re, json, subprocess, requests, time, base64

CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = "./xray"

def install_xray():
    if os.path.isfile(XRAY_BIN): return
    print("👠 Скачиваю Xray для господина...")
    # Добавлен флаг -o (overwrite), чтобы не было вопросов про README
    cmd = "curl -L -s https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o xray.zip && unzip -o -q xray.zip && chmod +x xray"
    subprocess.run(cmd, shell=True, check=True)

def test_vless(vless_link, sni_mask):
    try:
        user_info = vless_link.split("@")[0].split("//")[1]
        server_part = vless_link.split("@")[1].split("?")[0]
        address, port = server_part.split(":")
        params = dict(re.findall(r'([^&?=]+)=([^&?#]+)', vless_link))
        net_type = params.get("type", "tcp")

        config = {
            "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "socks"}],
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [{"address": address, "port": int(port), "users": [{"id": user_info, "encryption": "none"}]}]},
                "streamSettings": {
                    "network": net_type,
                    "security": "tls",
                    "tlsSettings": {"serverName": sni_mask, "allowInsecure": True},
                    "wsSettings": {"path": params.get("path", "/")} if net_type == "ws" else None,
                    "grpcSettings": {"serviceName": params.get("serviceName", "")} if net_type == "grpc" else None
                }
            }]
        }
        with open("config_tmp.json", "w") as f: json.dump(config, f)
        proc = subprocess.Popen([XRAY_BIN, "-c", "config_tmp.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        try:
            r = requests.get(CHECK_URL, proxies={"http":"socks5h://127.0.0.1:10808","https":"socks5h://127.0.0.1:10808"}, timeout=5)
            success = (r.status_code == 204)
        except: success = False
        finally: 
            proc.terminate()
            if os.path.exists("config_tmp.json"): os.remove("config_tmp.json")
        return success
    except: return False

def main():
    install_xray()
    token = os.getenv('WORKFLOW_TOKEN')
    repo = os.getenv('GITHUB_REPOSITORY')
    h = {"Authorization": f"token {token}"}
    
    sni_data = requests.get(f"https://api.github.com/repos/{repo}/contents/endpoints.txt", headers=h).json()
    sni_list = base64.b64decode(sni_data['content']).decode().split('\n')
    sni_list = [s.strip() for s in sni_list if s.strip()]

    r = requests.get(f"https://api.github.com/repos/{repo}/contents/input", headers=h)
    if r.status_code != 200: return
    
    working_masked_links = []
    files_to_delete = []

    for item in r.json():
        if item["name"] == ".keep": continue
        files_to_delete.append(item)
        raw_content = requests.get(item["download_url"]).text
        for line in raw_content.split('\n'):
            line = line.strip()
            if not line.startswith("vless://"): continue
            for sni in sni_list:
                if test_vless(line, sni):
                    base = line.split("?")[0]
                    new_link = f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Checked_{sni}"
                    working_masked_links.append(new_link)

    if working_masked_links:
        sub_url = f"https://api.github.com/repos/{repo}/contents/subscription.txt"
        curr = requests.get(sub_url, headers=h)
        sha = curr.json().get("sha") if curr.status_code == 200 else None
        final_content = "\n".join(sorted(set(working_masked_links)))
        requests.put(sub_url, headers=h, json={
            "message": "🔥 Verified Masked Nodes",
            "content": base64.b64encode(final_content.encode()).decode(),
            "sha": sha
        })

    for f in files_to_delete:
        requests.delete(f"https://api.github.com/repos/{repo}/contents/{f['path']}", headers=h, json={"message": "🧹 Clean", "sha": f["sha"]})

if __name__ == "__main__":
    main()
