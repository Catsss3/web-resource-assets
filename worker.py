
import os, re, json, subprocess, requests, time, base64

CHECK_URL = "https://www.gstatic.com/generate_204"
XRAY_BIN = "./xray"

def install_xray():
    if os.path.isfile(XRAY_BIN): return
    print("👠 Blondie ставит каблучки...")
    cmd = "curl -L -s https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o xray.zip && unzip -o -q xray.zip && chmod +x xray"
    subprocess.run(cmd, shell=True, check=True)

def test_vless(vless_link, sni_mask):
    try:
        # Упрощенный парсинг для скорости
        user_info = vless_link.split("@")[0].split("//")[1]
        server_part = vless_link.split("@")[1].split("?")[0]
        address, port = server_part.split(":")
        
        config = {
            "inbounds": [{"port": 10808, "listen": "127.0.0.1", "protocol": "socks"}],
            "outbounds": [{
                "protocol": "vless",
                "settings": {"vnext": [{"address": address, "port": int(port), "users": [{"id": user_info, "encryption": "none"}]}]},
                "streamSettings": {
                    "network": "ws", # Пробуем самые частые типы
                    "security": "tls",
                    "tlsSettings": {"serverName": sni_mask, "allowInsecure": True}
                }
            }]
        }
        with open("config_tmp.json", "w") as f: json.dump(config, f)
        proc = subprocess.Popen([XRAY_BIN, "-c", "config_tmp.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2) # Даем чуть больше времени на прогрев
        try:
            r = requests.get(CHECK_URL, proxies={"http":"socks5h://127.0.0.1:10808","https":"socks5h://127.0.0.1:10808"}, timeout=7)
            success = (r.status_code == 204)
        except: success = False
        finally: 
            proc.terminate()
        return success
    except: return False

def main():
    install_xray()
    SNI_PATH = "lists/active_endpoints.txt"
    if os.path.exists(SNI_PATH):
        with open(SNI_PATH, "r") as f:
            sni_list = [s.strip() for s in f if s.strip()]
    else:
        sni_list = ["v01.gosuslugi.ru"]

    working_links = []
    input_file = "input/fresh_raw_links.txt"
    
    if os.path.exists(input_file):
        with open(input_file, "r") as f:
            lines = f.readlines()
            print(f"🧐 Начинаю проверку {len(lines)} ссылок...")
            
            for line in lines[:150]: # Проверим 150 штук!
                line = line.strip()
                if not line.startswith("vless://"): continue
                
                # Пробуем на топовом SNI
                if test_vless(line, sni_list[0]):
                    print(f"✅ Нашла рабочую! {sni_list[0]}")
                    base = line.split("?")[0]
                    working_links.append(f"{base}?encryption=none&security=tls&sni={sni_list[0]}&type=ws#Blondie_Vip")

    if working_links:
        with open("subscription.txt", "w") as f:
            f.write("\n".join(working_links))
        print(f"🥳 УРА! Сохранила {len(working_links)} рабочих ссылок!")
    else:
        print("😿 К сожалению, в этой партии все ссылки оказались нерабочими.")

if __name__ == "__main__":
    main()
