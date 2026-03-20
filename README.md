# StegoAVI — Video Steganography using LSB and A5/1 Encryption

This project is a desktop application developed in Python for hiding messages inside video files using Least Significant Bit (LSB) steganography, with optional A5/1 encryption.

---

## Features

- Embed secret messages (text or file) into video
- Extract hidden messages from stego video
- Two insertion modes:
  - Sequential
  - Random (using stego-key)
- Optional encryption using A5/1 stream cipher
- File integrity verification using MD5
- Quality analysis:
  - PSNR (Peak Signal-to-Noise Ratio)
  - MSE (Mean Squared Error)
- Visualization:
  - RGB histogram
  - PSNR per frame
- Export metrics to CSV

---

## Methods

### Least Significant Bit (LSB)
Message bits are embedded into the least significant bits of pixel values in video frames.

### Random Insertion
Pixel positions are shuffled using a stego-key to increase security.

### A5/1 Encryption
Before embedding, the payload can be encrypted using A5/1 stream cipher with a 64-bit key.

---

## Application Overview

### Embed
- Input cover video
- Input message (text or file)
- Select insertion mode
- Optional encryption
- Generate stego video

### Extract
- Load stego video
- Input decryption key (if used)
- Extract message or file
- Verify integrity (MD5)

### Compare
- Compare original and stego video
- Display PSNR and MSE
- Show histogram and frame analysis

---

## Installation

```bash
git clone https://github.com/sonyaaputri/tugas2-kriptografi.git
cd tugas2-kriptografi
