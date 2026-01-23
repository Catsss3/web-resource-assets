
def run():
    with open("lists/active_endpoints.txt", "r") as f: sni = f.readline().strip()
    with open("input/fresh_raw_links.txt", "r") as f: links = [l.strip() for l in f if l.strip()]
    
    output = []
    for i, l in enumerate(links):
        base = l.split('?')[0]
        line = f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Blondie_Vip_{i+1}"
        output.append(line)
    
    # Соединяем строки настоящим символом переноса
    with open("subscription.txt", "w") as f:
        f.write('\n'.join(output))

if __name__ == '__main__':
    run()
