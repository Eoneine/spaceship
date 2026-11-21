# Logistics Analytics Copilot — Dashboard + Tanya-Jawab AI + Prediksi Permintaan

Aplikasi web untuk satu klien logistik: dashboard KPI dan grafik dari `mock_logistics_data.csv`, plus kolom tanya-jawab dalam bahasa biasa yang dijawab dari hasil hitungan data (bukan karangan AI).
AI (Gemini) cuma bertugas memahami pertanyaan dan memilih tool hitung yang tepat. Semua angka, grafik, dan prediksi dihitung oleh kode, dan setiap jawaban menunjukkan cara hitungnya.

## Untuk siapa
- **Reviewer assignment**: buka URL publik, langsung pakai tanpa login, cek kebenaran data, cara kerja AI, dan forecast.
- **Operator / manajer logistik (persona di soal)**: memantau performa pengiriman, bertanya cepat soal keterlambatan, dan merencanakan stok.
- **Lu sendiri saat presentasi/interview**: rancangannya sengaja sederhana dan mirip project yang sudah ada di CV lu (Olist Text-to-SQL bot, dashboard Looker/Power BI, model regresi), jadi gampang dijelasin.

## Fitur inti & pengalaman

**1. Dashboard (Descriptive)**
- 5 KPI: Total orders, Delivered, Delayed, On-time delivery rate, Average delivery time (hari).
- Grafik: volume order per bulan (garis), delivered on-time vs delayed (batang bertumpuk per bulan), breakdown per carrier (delay rate per carrier), breakdown per region/tujuan.
- Filter sederhana di atas: rentang tanggal, carrier, region. Semua KPI & grafik ikut berubah.

**2. Ask the Data (Diagnostic) — tanya dalam bahasa Inggris biasa**
- Contoh pertanyaan yang didukung:
  - "Show delayed orders by week for the last 3 months"
  - "Which carrier has the highest delay rate?"
  - "How many orders were delivered late last month?"
  - "Average delivery time by region", "Top 5 destinations by order value", "Order volume by category in Q3"
- Hasil: jawaban singkat 1–2 kalimat + grafik yang dipilih otomatis + tabel data mentah hasil agregasi.
- Pemilihan grafik otomatis berdasarkan bentuk hasil: deret waktu → garis, perbandingan kategori → batang, satu angka → kartu angka besar, komposisi kecil → donut.
- Tombol contoh pertanyaan (chip) supaya reviewer bisa langsung coba.

**3. Forecast (Predictive & Prescriptive)**
- Bisa lewat pertanyaan ("Predict demand for PAPER for the next 4 months", "How much inventory should I plan for BOOK?") atau lewat panel Forecast dengan pilihan kategori/SKU dan jumlah bulan.
- Level prediksi: per kategori produk. Kalau user minta SKU, SKU dipakai hanya jika historinya cukup (misal ≥ 6 bulan berisi); kalau tidak, sistem otomatis pakai tren kategorinya dan menjelaskan alasannya.
- Metode: regresi linear sederhana pada kuantitas bulanan, dibandingkan dengan moving average 3 bulan; yang error historisnya lebih kecil dipakai.
- Output: angka prediksi per bulan, grafik histori + forecast (garis putus-putus) dengan rentang perkiraan, rekomendasi stok = total prediksi + safety stock, dan penjelasan metode dalam bahasa sederhana.

**4. Explainability di setiap jawaban**
- Panel "How this was computed" (bisa dibuka-tutup): tool yang dipilih, filter (rentang waktu, carrier, status), metrik & dimensi, rencana query terstruktur (JSON), jumlah baris yang dihitung, dan definisi metrik (misal "delayed = status delayed").
- Tab "Data" berisi tabel hasil, bisa diunduh CSV.

**5. Batasan yang jujur**
- Pertanyaan di luar cakupan (misal "kenapa cuaca bikin telat?", data yang tidak ada di dataset) dijawab dengan pesan "not supported" + saran pertanyaan yang didukung, bukan jawaban karangan.
- Data hanya dibaca, tidak pernah diubah.

## Alur pengguna
1. Buka URL → langsung masuk Dashboard (KPI + grafik setahun 2025).
2. Atur filter → KPI dan grafik ter-update.
3. Pindah ke **Ask** → ketik pertanyaan atau klik contoh → lihat status singkat ("Interpreting… → Running query tool… ") → muncul jawaban, grafik, tabel, dan panel penjelasan.
4. Tanya forecast atau buka tab **Forecast** → pilih kategori/SKU + horizon → lihat grafik histori+prediksi, rekomendasi stok, dan penjelasan metode.
5. Riwayat pertanyaan dalam sesi tampil di samping supaya bisa diklik ulang.

Alur sistem yang ditunjukkan ke reviewer: Pertanyaan → AI menafsirkan → pilih tool (Query / Forecast) → input terstruktur divalidasi → dihitung kode → hasil → penjelasan → visualisasi.

## Nuansa UI/UX
- Gaya "control room" logistik: rapi, padat informasi tapi tenang, angka besar mudah dibaca, warna status jelas (on-time vs delayed).
- Tiga tab utama: Dashboard, Ask, Forecast. Tampilan responsif, enak juga di layar laptop reviewer.
- Animasi halus saat grafik muncul; tidak ada elemen dekoratif yang mengganggu data.

## Tahapan implementasi
**Fase 1 — MVP (dibangun sekarang)**
- Dashboard 5 KPI + 4 grafik + filter.
- Ask the Data dengan AI router (Gemini) → Query Tool + Forecast Tool, grafik otomatis, panel explainability, tabel data.
- Forecast per kategori (SKU jika data cukup) dengan regresi linear vs moving average, rekomendasi stok.
- Penolakan sopan untuk pertanyaan di luar cakupan.
- README lengkap (Inggris): cara setup & env variable, arsitektur & alur data, cara AI memilih tool, asumsi/batasan/pertanyaan yang tidak didukung, rencana pengembangan.
- Deploy ke URL publik.

**Fase 2 — Penguatan**
- Pertanyaan lanjutan dalam konteks ("now only for DHL"), perbandingan periode (bulan ini vs bulan lalu).
- Lebih banyak bentuk pertanyaan didukung (lead time per rute, dampak promo terhadap volume).
- Backtest forecast yang ditampilkan (akurasi pada 3 bulan terakhir).

**Fase 3 — Lanjutan**
- Exponential smoothing / musiman, forecast per warehouse.
- Upload dataset baru (tetap read-only), simpan & bagikan pertanyaan favorit.
- Notifikasi otomatis saat delay rate carrier melewati ambang.

## Asumsi
- AI: Gemini (model Flash terbaru: cepat dan murah, cukup untuk memilih tool) pakai API key Gemini milik lu sendiri dari Google AI Studio. Key diminta lewat form aman sebelum fitur Ask dibangun, disimpan sebagai secret, dan tidak pernah masuk repo. Biaya pemakaian masuk ke akun Google lu. Kalau key belum diisi atau kuotanya habis, Dashboard dan panel Forecast tetap jalan, dan hanya tab Ask yang menampilkan pesan "AI unavailable". Ini juga sesuai CV lu (pernah pakai Gemini API + LangChain di Hacktiv8). AI tidak menulis SQL bebas; AI hanya mengisi "rencana query" terstruktur (metrik, dimensi, filter, rentang waktu, granularity) yang divalidasi lalu dihitung oleh kode Python/Pandas.
- Tanpa login; tidak ada kredensial tes yang perlu dicantumkan.
- Tampilan aplikasi berbahasa Inggris; dokumen pendukung hanya README lengkap (Inggris). Catatan presentasi Bahasa Indonesia tidak dibuat.
- "Hari ini" untuk frasa relatif ("last month", "last 3 months") = tanggal order terakhir di dataset (31 Des 2025), bukan tanggal kalender sekarang. Ini dicantumkan di setiap jawaban.
- Definisi metrik: delayed = status `delayed`; delivered = status `delivered`; on-time rate = delivered / (delivered + delayed); waktu kirim = delivery_date − order_date, hanya untuk order yang punya delivery_date. Status `exception`, `in_transit`, `canceled` dihitung di total order tapi tidak di on-time rate.
- "Delivered late" ditafsirkan sama dengan status `delayed` (dataset tidak punya tanggal janji kirim).
- Permintaan (demand) = jumlah `quantity` per bulan; order `canceled` tidak dihitung.
- Safety stock = 1,65 × simpangan baku error bulanan (setara ~95% service level), dijelaskan di UI.
- Data CSV dimuat sekali saat aplikasi jalan dan diperlakukan read-only; ukuran 400 baris cukup dihitung di memori tanpa database analitik terpisah.
- Hubungan ke CV lu (untuk dijelaskan saat review): komputasi pakai Python + Pandas (skill inti lu), backend REST API setara Flask/Express yang pernah lu buat, pola "AI pilih tool + tampilkan query untuk audit" sama dengan Olist Text-to-SQL bot lu (bedanya di sini AI tidak menulis SQL bebas), forecast regresi linear sejalan dengan project Ridge Regression/Yandex, dan desain dashboard mengikuti pengalaman Looker/Power BI lu.
- README akan memuat bagian pengungkapan pemakaian alat AI saat membangun, karena soal menyebut pemakaian AI yang tidak diungkapkan bisa dinilai negatif.
- Deploy di hosting Emergent (soal membolehkan platform apa pun); secret tidak di-commit ke repo.
