import { readFile, writeFile } from "node:fs/promises";
import channles from "./telegram_channels.json" assert { type: "json" };

const CHANNELS_FILE = "./telegram_channels.json";
const BAD_CHANNELS_FILE = "./BadChannels.txt";

function extractTelegramChannels(text: string): string[] {
  const tgRegex = /https?:\/\/t\.me\/(?:s\/)?([A-Za-z0-9_]{5,})/g;
  const found = new Set<string>();
  let match: RegExpExecArray | null;

  while ((match = tgRegex.exec(text)) !== null) {
    const name = match[1];
    const ignore = ["s", "boost", "joinchat", "addstickers", "proxy", "socks", "socks5", "bot"];
    if (!ignore.includes(name.toLowerCase())) {
      found.add(name);
    }
  }
  return Array.from(found);
}

async function startHunter() {
  console.log("🚀 Stella Hunter: Выхожу на охоту...");
  
  const rawBad = await readFile(BAD_CHANNELS_FILE, "utf-8");
  const badSet = new Set(rawBad.split("\n").map(l => l.trim().toLowerCase()));
  const currentList = new Set(channles);
  const discoveredSet = new Set<string>();

  // Берем 50 случайных каналов из базы для поиска новых ссылок
  const shuffle = [...currentList].sort(() => 0.5 - Math.random()).slice(0, 50);

  for (const channel of shuffle) {
    try {
      const res = await fetch(`https://t.me/s/${channel}`);
      if (!res.ok) continue;
      
      const html = await res.text();
      const found = extractTelegramChannels(html);
      
      for (const name of found) {
        if (!currentList.has(name) && !badSet.has(name.toLowerCase())) {
          discoveredSet.add(name);
        }
      }
    } catch (e) {}
  }

  if (discoveredSet.size > 0) {
    const newList = [...currentList, ...Array.from(discoveredSet)];
    await writeFile(CHANNELS_FILE, JSON.stringify(newList, null, 2));
    console.log(`✅ Найдено новых источников: ${discoveredSet.size}`);
  } else {
    console.log("🤷 Новых каналов не обнаружено.");
  }
}

startHunter();
