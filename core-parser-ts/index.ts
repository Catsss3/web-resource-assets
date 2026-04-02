
import { appendFile } from "node:fs/promises";
import channles from "./telegram_channels.json" assert { type: "json" };

type Result = Record<"config" | "country" | "typeConfig", string>;
type FinalResult = Record<"protocol", string> & Result;

interface IPApiResponse {
  country: string; query: string; countryCode: string;
}

const countGetConfigOfEveryChannel = 2;
const countryFlagMap: { [key: string]: string } = {
  AF: "🇦🇫", AL: "🇦🇱", DZ: "🇩🇿", AD: "🇦🇩", AO: "🇦🇴", AG: "🇦🇬", AR: "🇦🇷", AM: "🇦🇲", AU: "🇦🇺", AT: "🇦🇹", AZ: "🇦🇿", BS: "🇧🇸", BH: "🇧🇭", BD: "🇧🇩", BB: "🇧🇧", BY: "🇧🇾", BE: "🇧🇪", BZ: "🇧🇿", BJ: "🇧🇯", BT: "🇧🇹", BO: "🇧🇴", BA: "🇧🇦", BW: "🇧🇼", BR: "🇧🇷", BN: "🇧🇳", BG: "🇧🇬", BF: "🇧🇫", BI: "🇧🇮", CV: "🇨🇻", KH: "🇰🇭", CM: "🇨🇲", CA: "🇨🇦", CF: "🇨🇫", TD: "🇹🇩", CL: "🇨🇱", CN: "🇨🇳", CO: "🇨🇴", KM: "🇰🇲", CG: "🇨🇬", CR: "🇨🇷", HR: "🇭🇷", CU: "🇨🇺", CY: "🇨🇾", CZ: "🇨🇿", CD: "🇨🇩", DK: "🇩🇰", DJ: "🇩🇯", DM: "🇩🇲", DO: "🇩🇴", EC: "🇪🇨", EG: "🇪🇬", SV: "🇸🇻", GQ: "🇬🇶", ER: "🇪🇷", EE: "🇪🇪", SZ: "🇸🇿", ET: "🇪🇹", FJ: "🇫🇯", FI: "🇫🇮", FR: "🇫🇷", GA: "🇬🇦", GM: "🇬🇲", GE: "🇬🇪", DE: "🇩🇪", GH: "🇬🇭", GR: "🇬🇷", GD: "🇬🇩", GT: "🇬🇹", GN: "🇬🇳", GW: "🇬🇼", GY: "🇬🇾", HT: "🇭🇹", HN: "🇭🇳", HU: "🇭🇺", IS: "🇮🇸", IN: "🇮🇳", ID: "🇮🇩", IR: "🇮🇷", IQ: "🇮🇶", IE: "🇮🇪", IL: "🇮🇱", IT: "🇮🇹", JM: "🇯🇲", JP: "🇯🇵", JO: "🇯🇴", KZ: "🇰🇿", KE: "🇰🇪", KI: "🇰🇮", KW: "🇰🇼", KG: "🇰🇬", LA: "🇱🇦", LV: "🇱🇻", LB: "🇱🇧", LS: "🇱🇸", LR: "🇱🇷", LY: "🇱🇾", LI: "🇱🇮", LT: "🇱🇹", LU: "🇱🇺", MG: "🇲🇬", MW: "🇲🇼", MY: "🇲🇾", MV: "🇲🇻", ML: "🇲🇱", MT: "🇲🇹", MH: "🇲🇭", MR: "🇲🇷", MU: "🇲🇺", MX: "🇲🇽", FM: "🇫🇲", MD: "🇲🇩", MC: "🇲🇨", MN: "🇲🇳", ME: "🇲🇪", MA: "🇲🇦", MZ: "🇲🇿", MM: "🇲🇲", NA: "🇳🇦", NR: "🇳🇷", NP: "🇳🇵", NL: "🇳🇱", NZ: "🇳🇿", NI: "🇳🇮", NE: "🇳🇪", NG: "🇳🇬", KP: "🇰🇵", MK: "🇲🇰", NO: "🇳🇴", OM: "🇴🇲", PK: "🇵🇰", PW: "🇵🇼", PS: "🇵🇸", PA: "🇵🇦", PG: "🇵🇬", PY: "🇵🇾", PE: "🇵🇪", PH: "🇵🇭", PL: "🇵🇱", PT: "🇵🇹", QA: "🇶🇦", RO: "🇷🇴", RU: "🇷🇺", RW: "🇷🇼", KN: "🇰🇳", LC: "🇱🇨", VC: "🇻🇨", WS: "🇼🇸", SM: "🇸🇲", ST: "🇸🇹", SA: "🇸🇦", SN: "🇸🇳", RS: "🇷🇸", SC: "🇸🇨", SL: "🇸🇱", SG: "🇸🇬", SK: "🇸🇰", SI: "🇸🇮", SB: "🇸🇧", SO: "🇸🇴", ZA: "🇿🇦", KR: "🇰🇷", SS: "🇸🇸", ES: "🇪🇸", LK: "🇱🇰", SD: "🇸🇩", SR: "🇸🇷", SE: "🇸🇪", CH: "🇨🇭", SY: "🇸🇾", TW: "🇹🇼", TJ: "🇹🇯", TZ: "🇹🇿", TH: "🇹🇭", TL: "🇹🇱", TG: "🇹🇬", TO: "🇹🇴", TT: "🇹🇹", TN: "🇹🇳", TR: "🇹🇷", TM: "🇹🇲", TV: "🇹🇻", UG: "🇺🇬", UA: "🇺🇦", AE: "🇦🇪", GB: "🇬🇧", US: "🇺🇸", UY: "🇺🇾", UZ: "🇺🇿", VU: "🇻🇺", VA: "🇻🇦", VE: "🇻🇪", VN: "🇻🇳", YE: "🇾🇪", ZM: "🇿🇲", ZW: "🇿🇼", UN: "🏴‍☠️"
};

function decodeHtmlEntities(str: string): string {
  return decodeURIComponent(str).replace(/&amp;/g, "&").replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&#039;/g, "'");
}

async function fetchHtml(url: string): Promise<void> {
  try {
    const response = await fetch(url, { redirect: "manual" });
    if (!response.ok) return;
    const html: string = await response.text();
    // ТОЛЬКО ЖИВЫЕ ПРОТОКОЛЫ
    const regex = /(vless|hysteria2|tuic):\/\/[^\s<>]+/gm;
    const matches = html.match(regex);
    if (matches) {
      const lastMessages = matches.slice(-countGetConfigOfEveryChannel);
      for (const element of lastMessages) {
        const decodeHtml = decodeHtmlEntities(element);
        if (!decodeHtml.includes("…")) await Grouping(decodeHtml);
      }
    }
  } catch (e) {}
}

async function configChanger(urlString: string): Promise<FinalResult> {
  const protocol = urlString.split("://")[0];
  const hostMatch = urlString.match(/@?([^:/#?]+)/);
  const hostname = hostMatch ? hostMatch[1] : "1.1.1.1";
  const api = await checkIP(hostname);
  const baseLink = urlString.split("#")[0];
  const newName = `${api.flag} ${api.countryCode} | ${protocol.toUpperCase()}`;
  let typeConfig = protocol;
  if (baseLink.includes("security=reality")) typeConfig = "reality";
  else if (protocol === "hysteria2" || protocol === "tuic") typeConfig = "quic";
  return { protocol, config: `${baseLink}#${newName}`, country: api.country, typeConfig };
}

async function checkIP(ipaddress: string) {
  try {
    const response = await fetch(`https://www.irjh.top/py/check/ip.php?ip=${ipaddress}`);
    const data = await response.json() as IPApiResponse;
    return { country: data.country || "Unknown", flag: countryFlagMap[data.countryCode] || "🏴‍☠️", ip: data.query || ipaddress, countryCode: data.countryCode || "UN" };
  } catch { return { country: "Unknown", flag: "🏴‍☠️", ip: ipaddress, countryCode: "UN" }; }
}

async function Grouping(urls: string): Promise<void> {
  const result = await configChanger(urls);
  if (result) {
    await appendFile(`./category/${result.protocol}.txt`, result.config + "\n");
    await appendFile(`./category/${result.country}.txt`, result.config + "\n");
    if (result.typeConfig && result.typeConfig !== result.protocol) {
      await appendFile(`./category/${result.typeConfig}.txt`, result.config + "\n");
    }
  }
}

async function startScaninig() {
  for (const value of channles) { await fetchHtml("https://t.me/s/" + value); }
}
startScaninig();
