# Xavier Trade — News Bot

Bot terpisah yang mengirim headline berita pasar beserta link-nya ke channel Discord `#news-update`.
Berjalan gratis di GitHub Actions setiap ±5 menit, tidak terhubung dengan Streamlit.

## Struktur

```
news-bot/
├── .github/workflows/news.yml   # jadwal GitHub Actions
├── news_bot.py                  # ambil RSS → simpan → kirim ke Discord
├── requirements.txt
└── .gitignore
```

## Cara setup

1. **Buat webhook Discord**
   Channel `#news-update` → Edit Channel → Integrations → Webhooks → New Webhook → Copy Webhook URL.

2. **Buat repo baru di GitHub** (disarankan *public* agar menit Actions tidak terbatas), lalu upload semua file di folder ini.
   Jangan upload URL webhook ke dalam kode.

3. **Simpan webhook sebagai secret**
   Repo → Settings → Secrets and variables → Actions → New repository secret
   - Name: `WEBHOOK_NEWS`
   - Secret: URL webhook dari langkah 1

4. **Jalankan pertama kali secara manual**
   Tab Actions → News Bot → Run workflow.
   Run pertama hanya menyimpan berita lama tanpa mengirim, supaya channel tidak dibanjiri.

5. Setelah itu bot berjalan otomatis setiap ±5 menit dan hanya mengirim berita baru.

## Pengaturan (di `news_bot.py`)

| Variabel | Fungsi |
|---|---|
| `FEEDS` | Daftar sumber RSS. Cek URL terbaru di situs masing-masing. |
| `KEYWORDS` | Filter judul. Kosongkan `[]` untuk mengirim semua berita. |
| `MAX_KIRIM_PER_RUN` | Batas berita per run agar channel tidak penuh. |

## Catatan

- Jadwal GitHub Actions bisa terlambat 5–15 menit saat server GitHub sibuk.
- GitHub menonaktifkan jadwal otomatis jika repo publik tidak ada aktivitas selama 60 hari. Cukup buka tab Actions dan aktifkan lagi, atau buat commit kecil.
- Database `news.db` disimpan lewat cache Actions. Jika cache terhapus, run berikutnya dianggap run pertama (menyimpan tanpa mengirim), jadi tidak terjadi pengiriman dobel.
