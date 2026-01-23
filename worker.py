
with open("lists/active_endpoints.txt", "r") as f: sni = f.readline().strip()
with open("input/fresh_raw_links.txt", "r") as f: links = f.readlines()
with open("subscription.txt", "w") as f:
    for i, l in enumerate(links):
        base = l.strip().split('?')[0]
        # Используем обычный print, он САМ добавит правильный перенос строки
        print(f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Blondie_Vip_{i+1}", file=f)
