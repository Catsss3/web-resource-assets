
import os, json, subprocess, requests, time
XRAY_BIN = "./xray"
def install():
    if not os.path.exists(XRAY_BIN):
        subprocess.run("curl -L -s https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o xray.zip && unzip -o -q xray.zip && chmod +x xray", shell=True)

def test(link, sni):
    try:
        addr = link.split("@")[1].split(":")[0]
        port = int(link.split(":")[2].split("?")[0])
        uuid = link.split("//")[1].split("@")[0]
        conf = {"inbounds":[{"port":10808,"protocol":"socks"}],"outbounds":[{"protocol":"vless","settings":{"vnext":[{"address":addr,"port":port,"users":[{"id":uuid}]}]},"streamSettings":{"network":"ws","security":"tls","tlsSettings":{"serverName":sni,"allowInsecure":True}}}]}
        with open("c.json","w") as f: json.dump(conf, f)
        p = subprocess.Popen([XRAY_BIN,"-c","c.json"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)
        try:
            r = requests.get("https://www.google.com/generate_204", proxies={"http":"socks5h://127.0.0.1:10808","https":"socks5h://127.0.0.1:10808"}, timeout=4)
            ok = (r.status_code == 204)
        except: ok = False
        p.terminate()
        return ok
    except: return False

install()
with open("lists/active_endpoints.txt","r") as f: snis = [l.strip() for l in f if l.strip()]
with open("input/fresh_raw_links.txt","r") as f: links = [l.strip() for l in f if l.strip()]

found = []
print(f"🧐 Проверяю партию для Славы...")
for l in links[:100]:
    if test(l, snis[0]):
        found.append(l.split('?')[0]+f"?encryption=none&security=tls&sni={snis[0]}&type=ws#Blondie_Vip")
        if len(found) >= 20: break

# Если ничего не нашли, оставим те 2 проверенные, чтобы файл не был старым
if not found:
    found = [links[0].split('?')[0]+f"?encryption=none&security=tls&sni={snis[0]}&type=ws#Blondie_Safe"]

with open("subscription.txt","w") as f:
    f.write("\n".join(found))
