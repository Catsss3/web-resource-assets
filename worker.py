
with open("lists/active_endpoints.txt", "r") as f: sni = f.readline().strip()
with open("input/fresh_raw_links.txt", "r") as f: links = [l.strip() for l in f if l.strip()]
with open("subscription.txt", "w") as f:
    # Пишем через print, он на Гитхабе ВСЕГДА делает нормальный перенос
    for i, l in enumerate(links):
        base = l.split('?')[0]
        print(f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Blondie_Vip_{i+1}", file=f)
