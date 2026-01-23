
import os
def start():
    with open("lists/active_endpoints.txt", "r") as f: sni = f.readline().strip()
    with open("input/fresh_raw_links.txt", "r") as f: links = [l.strip() for l in f if l.strip()]
    with open("subscription.txt", "w") as f:
        for i, l in enumerate(links):
            base = l.split('?')[0]
            f.write(f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Blondie_Auto_{i+1}\n")
if __name__ == '__main__':
    start()
