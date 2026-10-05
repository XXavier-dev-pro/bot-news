"""
News Bot - Xavier Trade
Mengambil berita dari RSS dan mengirim berita baru ke channel Discord #news-update.
"""
import os, sys, time, sqlite3
import feedparser, requests

WEBHOOK = os.environ.get("WEBHOOK_NEWS")
DB = "news.db"

FEEDS = {
    "CNBC Indonesia": "https://www.cnbcindonesia.com/market/rss",
    "Kontan": "https://rss.kontan.co.id/news/investasi",
}

KEYWORDS = ["saham", "ihsg", "emiten", "bursa", "bei", "dividen", "investor"]
MAX_KIRIM_PER_RUN = 15
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def relevan(judul):
    return not KEYWORDS or any(k in judul.lower() for k in KEYWORDS)


def ambil_feed(url):
    r = requests.get(url, headers=HEADERS, timeout=15)
    print(f"  HTTP {r.status_code}, {len(r.content)} bytes")
    r.raise_for_status()
    return feedparser.parse(r.content).entries


def kirim(judul, link, sumber):
    embed = {"title": judul[:256], "url": link, "color": 0x3498DB, "footer": {"text": sumber}}
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
    print("Run pertama" if run_pertama else "Database ditemukan (bukan run pertama)")

    con = sqlite3.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS news (link TEXT PRIMARY KEY, judul TEXT, "
                "sumber TEXT, waktu_simpan TEXT DEFAULT CURRENT_TIMESTAMP)")

    terkirim = 0
    for sumber, url in FEEDS.items():
        print(f"[{sumber}]")
        try:
            entries = ambil_feed(url)
        except Exception as e:
            print(f"  Gagal ambil: {e}")
            continue

        baru = lolos = 0
        for e in reversed(entries):
            link, judul = e.get("link"), e.get("title")
            if not link or not judul:
                continue
            cur = con.execute("INSERT OR IGNORE INTO news (link, judul, sumber) VALUES (?,?,?)",
                              (link, judul, sumber))
            if cur.rowcount != 1:
                continue
            baru += 1
            if run_pertama or not relevan(judul):
                continue
            lolos += 1
            if terkirim < MAX_KIRIM_PER_RUN and kirim(judul, link, sumber):
                terkirim += 1
                time.sleep(1)

        print(f"  {len(entries)} berita di feed, {baru} baru, {lolos} lolos filter")

    con.commit()
    con.close()
    print(f"Selesai. {terkirim} berita terkirim.")


if __name__ == "__main__":
    main()
