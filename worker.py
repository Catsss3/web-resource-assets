
import os, re, json, subprocess, requests, time, base64

CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = "./xray"

def install_xray():
    if os.path.isfile(XRAY_BIN): return
    print("👠 Blondie: Ставлю каблучки (Xray)...")
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
    
    # ПУТЬ К НАШЕМУ НОВОМУ СПИСКУ
    SNI_PATH = "lists/active_endpoints.txt"
    if os.path.exists(SNI_PATH):
        with open(SNI_PATH, "r") as f:
            sni_list = [s.strip() for s in f if s.strip()]
    else:
        sni_list = ["yandex.ru", "gosuslugi.ru"] # Фолбэк

    input_dir = "input"
    if not os.path.exists(input_dir): return
    
    working_masked_links = []
    
    for filename in os.listdir(input_dir):
        if filename == ".keep": continue
        filepath = os.path.join(input_dir, filename)
        with open(filepath, "r") as f:
            content = f.read()
            
        for line in content.split('\n'):
            line = line.strip()
            if not line.startswith("vless://"): continue
            
            # Проверяем на первых 5 SNI из списка для баланса скорости/качества
            for sni in sni_list[:5]:
                if test_vless(line, sni):
                    base = line.split("?")[0]
                    new_link = f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Blondie_{sni}"
                    working_masked_links.append(new_link)
                    break 

    if working_masked_links:
        with open("subscription.txt", "w") as f:
            f.write("\n".join(sorted(set(working_masked_links))))
        print(f"✨ Слава, я проверила всё! Рабочие ссылки в подписке.")

if __name__ == "__main__":
    main()
