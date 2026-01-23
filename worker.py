
import os
def run():
    try:
        with open("lists/active_endpoints.txt", "r") as f: sni = f.readline().strip()
        with open("input/fresh_raw_links.txt", "r") as f: links = [l.strip() for l in f if l.strip()]
        
        with open("subscription.txt", "w") as f:
            for i, l in enumerate(links[:50]):
                base = l.split('?')[0]
                # Гарантированный перенос строки для GitHub
                f.write(f"{base}?encryption=none&security=tls&sni={sni}&type=ws#Blondie_Auto_{i+1}\n")
        print("✅ Подписка обновлена успешно!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == '__main__':
    run()
