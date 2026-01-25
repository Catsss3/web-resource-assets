
import os
import shutil
import re

BASE_DIR = 'core-parser-ts/category'
FOLDERS = {
    'countries': [
        'Russia', 'Germany', 'United States', 'Netherlands',
        'France', 'Finland', 'Canada', 'United Kingdom', 'Turkey', 'Ukraine',
        'Japan', 'Singapore', 'Poland', 'Kazakhstan', 'Italy'
    ],
    'protocols': ['vless', 'vmess', 'trojan', 'ss', 'wireguard', 'shadowsocks'],
    'networks':  ['grpc', 'ws', 'tcp', 'http', 'h2', 'httpupgrade', 'xhttp']
}

for folder_name in FOLDERS:
    os.makedirs(os.path.join(BASE_DIR, folder_name), exist_ok=True)

def is_clean_name(name: str) -> bool:
    name_without_ext = name.rsplit('.txt', 1)[0]
    # Разрешаем буквы, цифры, пробелы, точки, дефисы и нижние подчеркивания
    return not re.search(r'[^a-zA-Z0-9\s.\-_]', name_without_ext)

for entry in os.listdir(BASE_DIR):
    src_path = os.path.join(BASE_DIR, entry)
    if not entry.lower().endswith('.txt') or os.path.isdir(src_path):
        continue

    name_low = entry.lower()
    moved = False

    for proto in FOLDERS['protocols']:
        if proto in name_low:
            dst_path = os.path.join(BASE_DIR, 'protocols', entry)
            shutil.move(src_path, dst_path)
            moved = True
            break
    if moved: continue

    for net in FOLDERS['networks']:
        if net in name_low:
            dst_path = os.path.join(BASE_DIR, 'networks', entry)
            shutil.move(src_path, dst_path)
            moved = True
            break
    if moved: continue

    if is_clean_name(entry):
        dst_path = os.path.join(BASE_DIR, 'countries', entry)
        shutil.move(src_path, dst_path)
    else:
        os.remove(src_path)

print("👱‍♀️ Stella: Сортировка завершена! Комната чиста.")
