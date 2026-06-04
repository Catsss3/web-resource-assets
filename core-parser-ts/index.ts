import { appendFile, readFile } from "node:fs/promises";
import channles from "./telegram_channels.json" assert { type: "json" };

interface IPApiResponse {
  country: string;
  query: string;
  countryCode: string;
}

// Сколько конфигов брать с каждого канала
const countGetConfigOfEveryChannel = 2;

// Разрешённые протоколы
const ALLOWED_PROTOCOLS = new Set(["vless", "hy2", "hysteria2", "tuic"]);

const countryFlagMap: { [key: string]: string } = {
  AF: "🇦🇫", AL: "🇦🇱", DZ: "🇩🇿", AD: "🇦🇩", AO: "🇦🇴", AG: "🇦🇬", AR: "🇦🇷", AM: "🇦🇲",
  AU: "🇦🇺", AT: "🇦🇹", AZ: "🇦🇿", BS: "🇧🇸", BH: "🇧🇭", BD: "🇧🇩", BB: "🇧🇧", BY: "🇧🇾",
  BE: "🇧🇪", BZ: "🇧🇿", BJ: "🇧🇯", BT: "🇧🇹", BO: "🇧🇴", BA: "🇧🇦", BW: "🇧🇼", BR: "🇧🇷",
  BN: "🇧🇳", BG: "🇧🇬", BF: "🇧🇫", BI: "🇧🇮", CV: "🇨🇻", KH: "🇰🇭", CM: "🇨🇲", CA: "🇨🇦",
  CF: "🇨🇫", TD: "🇹🇩", CL: "🇨🇱", CN: "🇨🇳", CO: "🇨🇴", KM: "🇰🇲", CG: "🇨🇬", CR: "🇨🇷",
  HR: "🇭🇷", CU: "🇨🇺", CY: "🇨🇾", CZ: "🇨🇿", CD: "🇨🇩", DK: "🇩🇰", DJ: "🇩🇯", DM: "🇩🇲",
  DO: "🇩🇴", EC: "🇪🇨", EG: "🇪🇬", SV: "🇸🇻", GQ: "🇬🇶", ER: "🇪🇷", EE: "🇪🇪", SZ: "🇸🇿",
  ET: "🇪🇹", FJ: "🇫🇯", FI: "🇫🇮", FR: "🇫🇷", GA: "🇬🇦", GM: "🇬🇲", GE: "🇬🇪", DE: "🇩🇪",
  GH: "🇬🇭", GR: "🇬🇷", GD: "🇬🇩", GT: "🇬🇹", GN: "🇬🇳", GW: "🇬🇼", GY: "🇬🇾", HT: "🇭🇹",
  HN: "🇭🇳", HU: "🇭🇺", IS: "🇮🇸", IN: "🇮🇳", ID: "🇮🇩", IR: "🇮🇷", IQ: "🇮🇶", IE: "🇮🇪",
  IL: "🇮🇱", IT: "🇮🇹", JM: "🇯🇲", JP: "🇯🇵", JO: "🇯🇴", KZ: "🇰🇿", KE: "🇰🇪", KI: "🇰🇮",
  KW: "🇰🇼", KG: "🇰🇬", LA: "🇱🇦", LV: "🇱🇻", LB: "🇱🇧", LS: "🇱🇸", LR: "🇱🇷", LY: "🇱🇾",
  LI: "🇱🇮", LT: "🇱🇹", LU: "🇱🇺", MG: "🇲🇬", MW: "🇲🇼", MY: "🇲🇾", MV: "🇲🇻", ML: "🇲🇱",
  MT: "🇲🇹", MH: "🇲🇭", MR: "🇲🇷", MU: "🇲🇺", MX: "🇲🇽", FM: "🇫🇲", MD: "🇲🇩", MC: "🇲🇨",
  MN: "🇲🇳", ME: "🇲🇪", MA: "🇲🇦", MZ: "🇲🇿", MM: "🇲🇲", NA: "🇳🇦", NR: "🇳🇷", NP: "🇳🇵",
  NL: "🇳🇱", NZ: "🇳🇿", NI: "🇳🇮", NE: "🇳🇪", NG: "🇳🇬", KP: "🇰🇵", MK: "🇲🇰", NO: "🇳🇴",
  OM: "🇴🇲", PK: "🇵🇰", PW: "🇵🇼", PS: "🇵🇸", PA: "🇵🇦", PG: "🇵🇬", PY: "🇵🇾", PE: "🇵🇪",
  PH: "🇵🇭", PL: "🇵🇱", PT: "🇵🇹", QA: "🇶🇦", RO: "🇷🇴", RU: "🇷🇺", RW: "🇷🇼", KN: "🇰🇳",
  LC: "🇱🇨", VC: "🇻🇨", WS: "🇼🇸", SM: "🇸🇲", ST: "🇸🇹", SA: "🇸🇦", SN: "🇸🇳", RS: "🇷🇸",
  SC: "🇸🇨", SL: "🇸🇱", SG: "🇸🇬", SK: "🇸🇰", SI: "🇸🇮", SB: "🇸🇧", SO: "🇸🇴", ZA: "🇿🇦",
  KR: "🇰🇷", SS: "🇸🇸", ES: "🇪🇸", LK: "🇱🇰", SD: "🇸🇩", SR: "🇸🇷", SE: "🇸🇪", CH: "🇨🇭",
  SY: "🇸🇾", TW: "🇹🇼", TJ: "🇹🇯", TZ: "🇹🇿", TH: "🇹🇭", TL: "🇹🇱", TG: "🇹🇬", TO: "🇹🇴",
  TT: "🇹🇹", TN: "🇹🇳", TR: "🇹🇷", TM: "🇹🇲", TV: "🇹🇻", UG: "🇺🇬", UA: "🇺🇦", AE: "🇦🇪",
  GB: "🇬🇧", US: "🇺🇸", UY: "🇺🇾", UZ: "🇺🇿", VU: "🇻🇺", VA: "🇻🇦", VE: "🇻🇪", VN: "🇻🇳",
  YE: "🇾🇪", ZM: "🇿🇲", ZW: "🇿🇼",
  UN: "🌐",
};

// ─────────────────────────────────────────────────────────────────────────────
// УНИВЕРСАЛЬНЫЙ ВАЛИДАТОР КОНФИГОВ
// Проверяет структуру ссылки — без привязки к конкретным доменам.
// Возвращает null если ссылка валидна, или строку с причиной блокировки.
// ─────────────────────────────────────────────────────────────────────────────
function validateConfig(url: string): string | null {

  // 1. Обрезанные ссылки — парсер гарантированно упадёт
  if (url.includes("…") || url.includes("...")) {
    return "обрезанная ссылка";
  }

  // 2. Слишком короткая ссылка — не может быть валидным конфигом
  if (url.length < 30) {
    return "слишком короткая ссылка";
  }

  // 3. Несовместимые транспорты — падение ядра при URL-тесте
  //    xhttp и mode=auto не поддерживаются старыми ядрами V2Ray/Xray
  if (/[?&]type=xhttp(&|$)/.test(url)) {
    return "несовместимый транспорт xhttp";
  }
  if (/[?&]mode=auto(&|#|$)/.test(url)) {
    return "несовместимый режим mode=auto";
  }

  // 4. Проверка параметра path= на вложенные ссылки / незакодированные знаки =
  //    Логика: декодируем значение path и ищем паттерны ссылок внутри него.
  //    Двоеточие само по себе разрешено (/path:8080 — валидно),
  //    но если внутри path сидит "://" — это явно вложенная ссылка.
  const pathMatch = url.match(/[?&]path=([^&#+]*)/);
  if (pathMatch) {
    try {
      const decodedPath = decodeURIComponent(pathMatch[1]);
      if (decodedPath.includes("://")) {
        return `вложенная ссылка в параметре path: "${decodedPath.substring(0, 40)}"`;
      }
      // Незакодированный знак = внутри path (признак склеенных параметров)
      // %3D — легитимный закодированный =, его пропускаем
      if (pathMatch[1].includes("=")) {
        return `незакодированный знак = в параметре path`;
      }
    } catch {
      return "невалидное URL-кодирование в параметре path";
    }
  }

  // 5. Хэштег с мусором, ломающим UI клиента.
  //    ВАЖНО: наш собственный формат "🌐 UN | VLESS" содержит |, поэтому
  //    проверяем только хэштеги, которые МЫ ЕЩЁ НЕ ПЕРЕПИСАЛИ.
  //    После configChanger хэштег будет чистым — проверяем исходник ДО него.
  const hashIndex = url.indexOf("#");
  if (hashIndex !== -1) {
    const namePart = url.slice(hashIndex + 1);
    // Признаки мусорного имени: URL-encoded последовательности в хэштеге
    // (эмодзи флаги в сыром виде = %F0%9F..., битые символы = %EF%BF%BD и т.д.)
    // Порог: больше 3 процентных последовательностей подряд — мусор
    const percentCount = (namePart.match(/%[0-9A-Fa-f]{2}/g) || []).length;
    if (percentCount > 5) {
      return `URL-мусор в хэштеге (${percentCount} закодированных символов)`;
    }
    // Слишком длинное имя конфига ломает UI некоторых клиентов
    if (namePart.length > 120) {
      return `слишком длинное имя конфига (${namePart.length} символов)`;
    }
  }

  // 6. Невалидный хост: IP-адрес 0.0.0.0 или 127.x.x.x — не имеет смысла
  const hostMatch = url.match(/(?:@|:\/\/)([^:/#?@[\]]+)/);
  if (hostMatch) {
    const host = hostMatch[1];
    if (host === "0.0.0.0" || host.startsWith("127.") || host === "localhost") {
      return `loopback/нулевой адрес хоста: ${host}`;
    }
    // Хост состоит только из цифр и точек, но не является валидным IPv4
    if (/^[\d.]+$/.test(host)) {
      const parts = host.split(".");
      if (parts.length !== 4 || parts.some(p => isNaN(+p) || +p > 255 || p === "")) {
        return `невалидный IP-адрес: ${host}`;
      }
    }
  }

  return null; // всё ок
}

// ─────────────────────────────────────────────────────────────────────────────

function decodeHtmlEntities(str: string): string {
  return decodeURIComponent(str)
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#039;/g, "'");
}

function tryDecodeBase64(str: string): string {
  try {
    const cleanStr = str.replace(/\s/g, "");
    if (cleanStr.length % 4 !== 0 && !cleanStr.endsWith("=")) return "";
    const decoded = Buffer.from(cleanStr, "base64").toString("utf-8");
    if (!/[\x20-\x7E]/.test(decoded)) return "";
    return decoded;
  } catch {
    return "";
  }
}

function isAllowedProtocol(protocol: string): boolean {
  return ALLOWED_PROTOCOLS.has(protocol.toLowerCase());
}

async function fetchHtml(url: string): Promise<void> {
  try {
    const response = await fetch(url, { redirect: "manual" });
    if (!response.ok) {
      console.warn(`[WARN] Не удалось получить страницу: ${url} (статус ${response.status})`);
      return;
    }

    const html: string = await response.text();

    const regex = /\b(vless|hysteria2|hy2|tuic):\/\/[^\s<>"']+/gm;
    let matches = html.match(regex) || [];

    const b64Regex = /[A-Za-z0-9+/]{40,}={0,2}/gm;
    const b64Matches = html.match(b64Regex) || [];
    for (const b64 of b64Matches) {
      const decoded = tryDecodeBase64(b64);
      if (!decoded) continue;
      const b64Links = decoded.match(regex);
      if (b64Links) matches = matches.concat(b64Links);
    }

    matches = [...new Set(matches)];
    if (matches.length === 0) return;

    const lastMessages = matches.slice(-countGetConfigOfEveryChannel);
    for (const element of lastMessages) {
      let decoded: string;
      try {
        decoded = decodeHtmlEntities(element);
      } catch {
        console.warn(`[БЛОК ДЕКОД] Не удалось декодировать: ${element.substring(0, 60)}`);
        continue;
      }

      // ── Универсальная проверка структуры ──
      const reason = validateConfig(decoded);
      if (reason) {
        console.warn(`[БЛОК] ${reason} → ${decoded.substring(0, 80)}...`);
        continue;
      }

      await Grouping(decoded);
    }
  } catch (e) {
    console.error(`[ERROR] fetchHtml(${url}):`, e);
  }
}

async function configChanger(urlString: string) {
  const protocolMatch = urlString.match(/^([a-z0-9]+):\/\//i);
  if (!protocolMatch) return null;

  const protocol = protocolMatch[1].toLowerCase();
  if (!isAllowedProtocol(protocol)) return null;

  const hostMatch = urlString.match(/(?:@|:\/\/)([^:/#?@[\]]+)/);
  const hostname = hostMatch ? hostMatch[1] : "1.1.1.1";

  const api = await checkIP(hostname);
  const baseLink = urlString.split("#")[0];
  const protocolLabel = protocol.toUpperCase();
  const newName = `${api.flag} ${api.countryCode} | ${protocolLabel}`;

  let typeConfig = protocol;
  if (protocol === "vless" && baseLink.includes("security=reality")) {
    typeConfig = "reality";
  } else if (protocol === "hysteria2" || protocol === "hy2" || protocol === "tuic") {
    typeConfig = "quic";
  }

  return {
    protocol,
    config: `${baseLink}#${newName}`,
    country: api.country,
    typeConfig,
  };
}

async function checkIP(ipaddress: string) {
  try {
    const response = await fetch(
      `https://www.irjh.top/py/check/ip.php?ip=${encodeURIComponent(ipaddress)}`
    );
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = (await response.json()) as IPApiResponse;
    return {
      country: data.country || "Unknown",
      flag: countryFlagMap[data.countryCode] ?? "🌐",
      ip: data.query || ipaddress,
      countryCode: data.countryCode || "UN",
    };
  } catch (e) {
    console.warn(`[WARN] checkIP(${ipaddress}):`, e);
    return { country: "Unknown", flag: "🌐", ip: ipaddress, countryCode: "UN" };
  }
}

async function Grouping(urls: string): Promise<void> {
  const result = await configChanger(urls);
  if (!result) return;

  const filesToUpdate: string[] = [
    `./category/protocols/${result.protocol}.txt`,
    `./category/countries/${result.country}.txt`,
  ];

  if (result.typeConfig !== result.protocol) {
    filesToUpdate.push(`./category/networks/${result.typeConfig}.txt`);
  }

  const baseConfig = result.config.split("#")[0];

  for (const filePath of filesToUpdate) {
    try {
      let content = "";
      try {
        content = await readFile(filePath, "utf-8");
      } catch {
        // Файл не существует — appendFile создаст его
      }

      if (content.includes(baseConfig)) continue;

      await appendFile(filePath, result.config + "\n");
      console.log(`[OK] Записан: ${result.config} → ${filePath}`);
    } catch (err) {
      console.error(`[ERROR] Grouping → запись в ${filePath}:`, err);
    }
  }
}

async function startScanning(): Promise<void> {
  console.log(`[START] Сканирование ${channles.length} каналов...`);
  for (const channel of channles) {
    const url = `https://t.me/s/${channel}`;
    console.log(`[SCAN] ${url}`);
    await fetchHtml(url);
  }
  console.log("[DONE] Сканирование завершено.");
}

startScanning();
