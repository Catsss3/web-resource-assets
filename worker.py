
import os, json, subprocess, requests, time

def install():
    if not os.path.exists("./xray"):
        subprocess.run("curl -L -s https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip -o xray.zip && unzip -o -q xray.zip && chmod +x xray", shell=True)

install()

# Читаем ссылки из нашего 'чулка'
with open("input/fresh_raw_links.txt", "r") as f:
    raw_links = [l.strip() for l in f if l.strip()]

# Просто берем и силой записываем их с твоим SNI (даже без теста, чтобы ты увидел ОБНОВЛЕНИЕ)
# Слава, это чтобы проверить, что Гитхаб ВООБЩЕ может писать в файл!
with open("subscription.txt", "w") as f:
    for l in raw_links[:5]:
        base = l.split('?')[0]
        f.write(f"{base}?encryption=none&security=tls&sni=v01.gosuslugi.ru&type=ws#Blondie_FORCE_UPDATE\n")

print("🔥 Силовой файл создан! Отправляю в GitHub...")
