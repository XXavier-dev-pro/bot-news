"""
News Bot - Xavier Trade
Mengambil berita dari banyak sumber (via Google News RSS) dan mengirim
berita baru ke channel Discord #news-update.
"""
import os, sys, time, sqlite3
from urllib.parse import quote_plus
import feedparser, requests

WEBHOOK = os.environ.get("WEBHOOK_NEWS")
DB = "news.db"

# Topik berita yang dicari
TOPIK = "saham OR IHSG OR emiten OR bursa OR dividen"

# Sumber berita: nama tampilan -> domain situs
SUMBER = {
    "CNBC Indonesia": "cnbcindonesia.com",
    "Kontan": "kontan.co.id",
    "Bisnis.com": "bisnis.com",
    "Investor.id": "investor.id",
    "IDX Channel": "idxchannel.com",
    "Detik Finance": "finance.detik.com",
    "Kompas Money": "money.kompas.com",
    "CNN Indonesia": "cnnindonesia.com",
    "Liputan6": "liputan6.com",
    "Emiten News": "emitennews.com",
    "Stockbit Snips": "snips.stockbit.com",
}

KEYWORDS = ["saham", "ihsg", "emiten", "bursa", "bei", "dividen", "investor",
            "ipo", "rights issue", "buyback", "laba", "kinerja"]
MAX_KIRIM_PER_RUN = 10
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def url_feed(domain):
    q = quote_plus(f"({TOPIK}) site:{domain} when:1d")
    return f"https://news.google.com/rss/search?q={q}&hl=id&gl=ID&ceid=ID:id"


def bersihkan_judul(judul):
    # Google News menambahkan " - Nama Sumber" di akhir judul
    return judul.rsplit(" - ", 1)[0].strip()


def relevan(judul):
    return not KEYWORDS or any(k in judul.lower() for k in KEYWORDS)


def kirim(judul, link, sumber):
    embed = {"title": judul[:256], "url": link, "color": 0x3498DB,
             "footer": {"text": sumber}}
    try:
        r = requests.post(WEBHOOK, json={"embeds": [embed]}, timeout=10)
        if r.status_code == 429:
            time.sleep(float(r.json().get("retry_after", 2)))
            r = requests.post(WEBHOOK, json={"embeds": [embed]}, timeout=10)
        if r.status_code != 204:
            print(f"  Discord menolak: {r.status_code} {r.text[:200]}")
        return r.status_code == 204
    except requests.RequestException as e:
        print(f"  Gagal kirim: {e}")
        return False


def main():
    if not WEBHOOK:
        sys.exit("WEBHOOK_NEWS belum diset di GitHub Secrets.")

    run_pertama = not os.path.exists(DB)
    print("Run pertama" if run_pertama else "Database ditemukan")

    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY, judul TEXT, "
                "sumber TEXT, waktu_simpan TEXT DEFAULT CURRENT_TIMESTAMP)")

    # Kumpulkan berita baru dari semua sumber
    antrian = []
    for nama, domain in SUMBER.items():
        try:
            r = requests.get(url_feed(domain), headers=HEADERS, timeout=15)
            r.raise_for_status()
            entries = feedparser.parse(r.content).entries
        except Exception as e:
            print(f"[{nama}] gagal: {e}")
            continue

        baru = 0
        for e in entries:
            link, judul = e.get("link"), e.get("title")
            if not link or not judul:
                continue
            judul = bersihkan_judul(judul)

            # Lewati jika link ATAU judul yang sama sudah pernah tersimpan
            sudah_ada = con.execute("SELECT 1 FROM news WHERE link=? OR judul=?",
                                    (link, judul)).fetchone()
            if sudah_ada:
                continue
            con.execute("INSERT INTO news (link, judul, sumber) VALUES (?,?,?)",
                        (link, judul, nama))
            baru += 1
            if not run_pertama and relevan(judul):
                waktu = e.get("published_parsed") or time.gmtime(0)
                antrian.append((waktu, judul, link, nama))

        print(f"[{nama}] {len(entries)} di feed, {baru} baru")

    con.commit()

    # Kirim dari yang terlama ke terbaru
    antrian.sort(key=lambda x: x[0])
    terkirim = 0
    for _, judul, link, nama in antrian[-MAX_KIRIM_PER_RUN:]:
        if kirim(judul, link, nama):
            terkirim += 1
            time.sleep(1)

    con.close()
    print(f"{len(antrian)} lolos filter, {terkirim} terkirim.")


if __name__ == "__main__":
    main()
