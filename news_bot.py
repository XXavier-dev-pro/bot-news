"""
News Bot - Xavier Trade
Mengambil berita dari RSS dan mengirim berita baru ke channel Discord #news-update.
Dijalankan sekali per run oleh GitHub Actions (setiap 5 menit).
"""

import os
import sys
import time
import sqlite3

import feedparser
import requests

WEBHOOK = os.environ.get("WEBHOOK_NEWS")
DB = "news.db"

# Sumber berita. Cek dan sesuaikan URL RSS terbaru di situs masing-masing.
FEEDS = {
    "CNBC Indonesia": "https://www.cnbcindonesia.com/market/rss",
    "Kontan": "https://rss.kontan.co.id/news/investasi",
}

# Opsional: hanya kirim berita yang judulnya mengandung kata kunci ini.
# Kosongkan list ( [] ) untuk mengirim semua berita.
KEYWORDS = ["saham", "ihsg", "emiten", "bursa", "bei", "dividen", "investor"]

MAX_KIRIM_PER_RUN = 15  # batas agar channel tidak dibanjiri


def relevan(judul: str) -> bool:
    if not KEYWORDS:
        return True
    j = judul.lower()
    return any(k in j for k in KEYWORDS)


def kirim(judul: str, link: str, sumber: str) -> bool:
    embed = {
        "title": judul[:256],
        "url": link,
        "color": 0x3498DB,
        "footer": {"text": sumber},
    }
    try:
        r = requests.post(WEBHOOK, json={"embeds": [embed]}, timeout=10)
        if r.status_code == 429:  # rate limit Discord
            time.sleep(float(r.json().get("retry_after", 2)))
            r = requests.post(WEBHOOK, json={"embeds": [embed]}, timeout=10)
        return r.status_code == 204
    except requests.RequestException as e:
        print(f"Gagal kirim: {e}")
        return False


def main():
    if not WEBHOOK:
        sys.exit("WEBHOOK_NEWS belum diset di GitHub Secrets.")

    run_pertama = not os.path.exists(DB)
    con = sqlite3.connect(DB)
    con.execute(
        "CREATE TABLE IF NOT EXISTS news ("
        "link TEXT PRIMARY KEY, judul TEXT, sumber TEXT, "
        "waktu_simpan TEXT DEFAULT CURRENT_TIMESTAMP)"
    )

    terkirim = 0
    for sumber, url in FEEDS.items():
        try:
            entries = feedparser.parse(url).entries
        except Exception as e:
            print(f"Gagal ambil {sumber}: {e}")
            continue

        for e in reversed(entries):  # dari yang terlama ke terbaru
            link, judul = e.get("link"), e.get("title")
            if not link or not judul:
                continue

            cur = con.execute(
                "INSERT OR IGNORE INTO news (link, judul, sumber) VALUES (?,?,?)",
                (link, judul, sumber),
            )
            berita_baru = cur.rowcount == 1

            # Run pertama hanya menyimpan, tidak mengirim (agar berita lama tidak membanjiri)
            if berita_baru and not run_pertama and relevan(judul):
                if terkirim >= MAX_KIRIM_PER_RUN:
                    continue
                if kirim(judul, link, sumber):
                    terkirim += 1
                    time.sleep(1)

    con.commit()
    con.close()

    if run_pertama:
        print("Run pertama: berita lama disimpan tanpa dikirim.")
    else:
        print(f"Selesai. {terkirim} berita terkirim.")


if __name__ == "__main__":
    main()
