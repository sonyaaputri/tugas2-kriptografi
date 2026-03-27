# StegoAVI — Steganografi Video Menggunakan LSB dan Enkripsi A5/1

Proyek ini adalah aplikasi desktop yang dikembangkan dengan Python untuk menyembunyikan pesan di dalam file video menggunakan steganografi Least Significant Bit (LSB), dengan enkripsi A5/1 opsional.

---

## Fitur

- Sembunyikan pesan rahasia (teks atau file) ke dalam video
- Ekstrak pesan tersembunyi dari video stego
- Dua mode penyisipan:
  - Sekuensial
  - Acak (menggunakan stego-key)
- Enkripsi opsional menggunakan A5/1 stream cipher
- Verifikasi integritas file menggunakan MD5
- Analisis kualitas:
  - PSNR (Peak Signal-to-Noise Ratio)
  - MSE (Mean Squared Error)
- Visualisasi:
  - Histogram RGB
  - PSNR per frame
- Ekspor metrik ke CSV

---

## Metode

### Least Significant Bit (LSB)
Bit pesan disematkan ke dalam bit paling signifikan dari nilai piksel dalam frame video.

### Penyisipan Acak
Posisi piksel dikocok menggunakan stego-key untuk meningkatkan keamanan.

### Enkripsi A5/1
Sebelum penyisipan, payload dapat dienkripsi menggunakan A5/1 stream cipher dengan kunci 64-bit.

---

## Teknologi yang Digunakan

- **Bahasa Pemrograman**: Python 3.8+
- **GUI Framework**: CustomTkinter (Modern Tkinter)
- **Computer Vision**: OpenCV (cv2)
- **Pemrosesan Gambar**: Pillow, NumPy
- **Visualisasi**: Matplotlib

---

## Dependencies

Semua dependencies tercantum dalam `requirements.txt`:

```
customtkinter
opencv-python
Pillow
numpy
matplotlib
```

---

## Instalasi & Setup

### 1. Clone Repository
```bash
git clone https://github.com/sonyaaputri/tugas2-kriptografi.git
cd tugas2-kriptografi
```

### 2. Buat Virtual Environment (Disarankan)
```bash
# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate
```

### 3. Instal Dependensi
```bash
pip install -r requirements.txt
```

---

##Tab ** - Sembunyikan pesan/file ke video
- Pilih video cover
- Input pesan (teks atau file)
- Pilih mode: Sekuensial atau Acak
- Opsional: Aktifkan enkripsi A5/1
- Generate video stego

**Tab Ekstrak** - Ekstrak pesan dari video stego
- Muat video stego
- Masukkan kunci dekripsi (jika dienkripsi)
- Ekstrak dan verifikasi integritas menggunakan MD5

**Tab Bandingkan** - Bandingkan video original dan stego
- Lihat metrik PSNR dan MSE
- Visualisasi histogram RGB
- Analisis PSNR per frameA5/1
- Generate stego video

**Extract Tab** - Ekstrak pesan dari video stego
- Load stego video
- Masukkan decryption key (jika dienkripsi)
- Extract dan verify integrity

**Compare Tab** - Bandingkan video original dan stego
- Lihat metrik PSNR dan MSE
- Visualisasi histogram RGB
- Analisis frame-by-frame PSNR

---

## Kredit

Project ini dibuat untuk memenuhi Tugas 2 II4021 Kriptografi.

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/snachkzs">
        <img src="https://github.com/snachkzs.png" width="80" style="border-radius: 50%"><br/>
        <strong>Alma Felicia Vielrizki</strong><br/>
        18223112
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/sonyaaputri">
        <img src="https://github.com/sonyaaputri.png" width="80" style="border-radius: 50%"><br/>
        <strong>Sonya Putri Fadilah</strong><br/>
        18223138
      </a>
    </td>
    <td align="center">
      <a href="https://github.com/auliaazkaazzahra">
        <img src="https://github.com/auliaazkaazzahra.png" width="80" style="border-radius: 50%"><br/>
        <strong>Aulia Azka Azzahra</strong><br/>
        18223131
      </a>
    </td>  
  </tr>
</table>