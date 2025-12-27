import os, re, json, subprocess, requests, time, base64

CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = "./xray"

def install_xray():
    if os.path.isfile(XRAY_BIN): return
    print("👠 Скачиваю Xray для господина...")
    cmd = "curl -L -s https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o xray.zip && unzip -q xray.zip && chmod +x xray"
    subprocess.run(cmd, shell=True, check=True)

def test_vless(vless_link, sni_mask):
    try:
        # Извлекаем данные
        user_info = vless_link.split("@")[0].split("//")[1]
        server_part = vless_link.split("@")[1].split("?")[0]
        address, port = server_part.split(":")
        
        # Парсим параметры, чтобы сохранить network (ws/grpc/tcp)
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
        
        with open("config.json", "w") as f: json.dump(config, f)
        
        proc = subprocess.Popen([XRAY_BIN, "-c", "config.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        
        try:
            r = requests.get(CHECK_URL, proxies={"http":"socks5h://127.0.0.1:10808","https":"socks5h://127.0.0.1:10808"}, timeout=5)
            success = (r.status_code == 204)
        except: success = False
        finally: proc.terminate()
        return success
    except: return False

def main():
    install_xray()
    
    # Получаем SNI
    sni_data = requests.get(f"https://api.github.com/repos/{os.getenv('GITHUB_REPOSITORY')}/contents/endpoints.txt", headers={"Authorization": f"token {os.getenv('WORKFLOW_TOKEN')}"}).json()
    sni_list = base64.b64decode(sni_data['content']).decode().split('\n')
    sni_list = [s.strip() for s in sni_list if s.strip()]

    # Получаем файлы из input
    r = requests.get(f"https://api.github.com/repos/{os.getenv('GITHUB_REPOSITORY')}/contents/input", headers={"Authorization": f"token {os.getenv('WORKFLOW_TOKEN')}"})
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
            
            print(f"🧐 Тестируем базу: {line[:50]}...")
            for sni in sni_list:
                if test_vless(line, sni):
                    # Собираем рабочую ссылку с новой маской
                    base = line.split("?")[0]
                    # Очищаем старые параметры и ставим новые
                    new_link = f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Checked_{sni}"
                    working_masked_links.append(new_link)
                    print(f"✅ Маска {sni} РАБОТАЕТ")

    if working_masked_links:
        # Пушим в subscription.txt
        sub_url = f"https://api.github.com/repos/{os.getenv('GITHUB_REPOSITORY')}/contents/subscription.txt"
        curr = requests.get(sub_url, headers={"Authorization": f"token {os.getenv('WORKFLOW_TOKEN')}"})
        sha = curr.json().get("sha") if curr.status_code == 200 else None
        
        final_content = "\n".join(sorted(set(working_masked_links)))
        requests.put(sub_url, headers={"Authorization": f"token {os.getenv('WORKFLOW_TOKEN')}"}, json={
            "message": "🔥 Updated with Verified Masked Nodes",
            "content": base64.b64encode(final_content.encode()).decode(),
            "sha": sha
        })

    # Чистка
    for f in files_to_delete:
        requests.delete(f"https://api.github.com/repos/{os.getenv('GITHUB_REPOSITORY')}/contents/{f['path']}", 
                        headers={"Authorization": f"token {os.getenv('WORKFLOW_TOKEN')}"}, 
                        json={"message": "🧹 Clean", "sha": f["sha"]})

if __name__ == "__main__":
    main()
