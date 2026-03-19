import math
import random
from typing import Iterable

import cv2
import numpy as np

from .a51 import a51

# Metadata belum diimplementasi, kalau udah uncomment 1 line dibawah ini sama sesuaiin aja
# from .metadata import HEADER_BASE_SIZE, build_header, parse_header

# TODO: saat metadata udah diimplementasi hapus yang bawah
try:
    from .metadata import HEADER_BASE_SIZE, build_header, parse_header
    METADATA_ENABLED = True
except Exception:
    METADATA_ENABLED = False
    HEADER_BASE_SIZE = 8

    def build_header(payload_len: int,
                     is_file: bool,
                     filename: str,
                     encrypted: bool,
                     random_mode: bool) -> bytes:
        return b""

    def parse_header(data: bytes) -> dict:
        raise NotImplementedError("Metadata parser belum diimplementasi.")
    
#hapus sampe sini


def_rgb = (3, 3, 2)


def rgb_bits(scheme: tuple[int, int, int] ):

    if len(scheme) != 3:
        raise ValueError("Skema harus terdiri dari 3 nilai: (R, G, B).") #nanti dari guinya apakah mungkin ini terjadi

    n_r, n_g, n_b = (int(scheme[0]), int(scheme[1]), int(scheme[2]))

    if (n_r, n_g, n_b) == (0, 0, 0):
        return def_rgb

    if not all(1 <= n <= 4 for n in (n_r, n_g, n_b)):
        raise ValueError("Setiap nilai R/G/B harus berada pada rentang 1-4.")

    return (n_r, n_g, n_b)

def bytes_to_bits(data: bytes):
    bits= []
    for byte in data:
        for i in range(8):
            bits.append((byte >> (7 - i)) & 1)
    return bits


def bits_to_bytes(bits: Iterable[int]):
    bit_list = list(bits)
    while len(bit_list) % 8 != 0:
        bit_list.append(0)

    result = []
    for i in range(0, len(bit_list), 8):
        byte = 0
        for b in bit_list[i:i + 8]:
            byte = (byte << 1) | int(b)
        result.append(byte)
    return bytes(result)


def embed_bits_in_pixel(
    pixel: tuple[int, int, int],
    bits: list[int],
    scheme: tuple[int, int, int] = def_rgb,
    ):

    n_r, n_g, n_b = rgb_bits(scheme)
    r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
    idx = 0

    for i in range(n_r - 1, -1, -1):
        if idx < len(bits):
            r = (r & ~(1 << i)) | (bits[idx] << i)
            idx += 1

    for i in range(n_g - 1, -1, -1):
        if idx < len(bits):
            g = (g & ~(1 << i)) | (bits[idx] << i)
            idx += 1

    for i in range(n_b - 1, -1, -1):
        if idx < len(bits):
            b = (b & ~(1 << i)) | (bits[idx] << i)
            idx += 1

    return (r, g, b)


def extract_bits_from_pixel(
    pixel: tuple[int, int, int],
    scheme: tuple[int, int, int] = def_rgb,
    ):

    n_r, n_g, n_b = rgb_bits(scheme)
    r, g, b = int(pixel[0]), int(pixel[1]), int(pixel[2])
    bits = []

    for i in range(n_r - 1, -1, -1):
        bits.append((r >> i) & 1)
    for i in range(n_g - 1, -1, -1):
        bits.append((g >> i) & 1)
    for i in range(n_b - 1, -1, -1):
        bits.append((b >> i) & 1)

    return bits


def calculate_capacity(video_path: str, scheme: tuple[int, int, int] = def_rgb):
    # ketentuan tambahan menolak penyisipan jika ukuran pesan rahasia melebihi batas kapasitas sisip
    scheme = rgb_bits(scheme)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka video: {video_path}")

    total_pixels = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        total_pixels += h * w

    cap.release()

    bits_per_pixel = sum(scheme)
    return (total_pixels * bits_per_pixel) // 8

def validate_capacity(
    video_path: str,
    data_to_embed: bytes,
    scheme: tuple[int, int, int] = def_rgb,
    ):

    return len(data_to_embed) <= calculate_capacity(video_path, scheme)


def calculate_mse_psnr(original_frame: np.ndarray, stego_frame: np.ndarray):
    max_i = 255.0
    mse = np.mean((original_frame.astype(float) - stego_frame.astype(float)) ** 2)

    if mse == 0:
        psnr = float("inf")
    else:
        psnr = 10 * math.log10((max_i ** 2) / mse)

    return float(mse), float(psnr)


def calculate_video_mse_psnr(original_path: str, stego_path: str):
    cap_original = cv2.VideoCapture(original_path)
    cap_stego = cv2.VideoCapture(stego_path)

    mse_list = []
    psnr_list = []

    while True:
        ret1, f1 = cap_original.read()
        ret2, f2 = cap_stego.read()
        if not ret1 or not ret2:
            break
        mse, psnr = calculate_mse_psnr(f1, f2)
        mse_list.append(mse)
        psnr_list.append(psnr)

    cap_original.release()
    cap_stego.release()

    finite_psnr = [p for p in psnr_list if p != float("inf")]
    mse_avg = float(np.mean(mse_list)) if mse_list else 0.0
    psnr_avg = float(np.mean(finite_psnr)) if finite_psnr else float("inf")

    return mse_list, psnr_list, mse_avg, psnr_avg


def embed_to_video(
    cover_path: str,
    output_path: str,
    payload: bytes,
    is_file: bool,
    filename: str = "",
    encrypt: bool = False,
    a51_key: bytes | None = None,
    random_mode: bool = False,
    stego_key: str = "",
    scheme: tuple[int, int, int] = def_rgb,
    ):
    scheme = rgb_bits(scheme)

    #Enkripsi a51 jika dipilih
    if encrypt and a51_key:
        payload_to_embed = a51.encrypt_payload(a51_key, payload)
    else:
        payload_to_embed = payload

    # TODO: bikin header kalau udah ada metadata
    #bawah ini apus aja kalau metadata udah diimplementasi
    if METADATA_ENABLED:
        header = build_header(
            payload_len=len(payload_to_embed),
            is_file=is_file,
            filename=filename,
            encrypted=encrypt,
            random_mode=random_mode,
        )
        full_data = header + payload_to_embed
    else:
        full_data = payload_to_embed
    #apus sampe sini

    # Validasi kapasitas sebelum mulai penyisipan
    if not validate_capacity(cover_path, full_data, scheme):
        cap = calculate_capacity(cover_path, scheme)
        raise ValueError(
            f"Data ({len(full_data)} bytes) melebihi kapasitas video ({cap} bytes)."
        )

    bit_stream = bytes_to_bits(full_data)
    total_bits = len(bit_stream)

    cap = cv2.VideoCapture(cover_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka video: {cover_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    bits_per_pixel = sum(scheme)
    bit_idx = 0
    done = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if not done:
            h, w = frame.shape[:2]
            total_pixels = h * w

            if random_mode and stego_key:
                pixel_indices = list(range(total_pixels))
                rng = random.Random(stego_key)
                rng.shuffle(pixel_indices)
            else:
                pixel_indices = list(range(total_pixels))

            frame_flat = frame.reshape(-1, 3)

            for pix_idx in pixel_indices:
                if bit_idx >= total_bits:
                    done = True
                    break

                chunk = bit_stream[bit_idx: bit_idx + bits_per_pixel]
                while len(chunk) < bits_per_pixel:
                    chunk.append(0)

                r_new, g_new, b_new = embed_bits_in_pixel(
                    (frame_flat[pix_idx][2], frame_flat[pix_idx][1], frame_flat[pix_idx][0]), chunk, scheme)
                frame_flat[pix_idx] = [b_new, g_new, r_new]
                bit_idx += bits_per_pixel

            frame = frame_flat.reshape(h, w, 3)

        out.write(frame)

    cap.release()
    out.release()

    return calculate_video_mse_psnr(cover_path, output_path)


def _extract_bits_random(
    cap: cv2.VideoCapture,
    bits_needed: int,
    scheme: tuple[int, int, int],
    random_mode: bool,
    stego_key: str,
    ):
    #Ekstraksi bit dari video dengan acak berdasarkan stego key

    extracted_bits = []

    while len(extracted_bits) < bits_needed:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        total_pix = h * w
        frame_flat = frame.reshape(-1, 3)

        if random_mode and stego_key:
            pixel_indices = list(range(total_pix))
            rng = random.Random(stego_key)
            rng.shuffle(pixel_indices)
        else:
            pixel_indices = list(range(total_pix))

        for pix_idx in pixel_indices:
            bits = extract_bits_from_pixel(
                (frame_flat[pix_idx][2], frame_flat[pix_idx][1], frame_flat[pix_idx][0]),
                scheme,
            )
            extracted_bits.extend(bits)
            if len(extracted_bits) >= bits_needed:
                break

    return extracted_bits


def extract_from_video(
    stego_path: str,
    a51_key: bytes | None = None,
    stego_key: str = "",
    scheme: tuple[int, int, int] = def_rgb,
    ):

    scheme = rgb_bits(scheme)

    cap = cv2.VideoCapture(stego_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka video: {stego_path}")

    # kalau metadata udah implementasi apus bawah ini
    if not METADATA_ENABLED:
        # TODO: tanpa metadata, payload_len tidak diketahui saat ekstraksi.
        raise NotImplementedError("Ekstraksi butuh metadata untuk membaca payload_len.")
    #apus sampe sini

    max_header_bytes = HEADER_BASE_SIZE + 255
    bits_needed_header = max_header_bytes * 8

    header_bits = _extract_bits_random(
        cap=cap,
        bits_needed=bits_needed_header,
        scheme=scheme,
        random_mode=False,
        stego_key="",
    )
    header_bytes = bits_to_bytes(header_bits[:bits_needed_header])
    meta = parse_header(header_bytes)

    header_size = meta["header_total_size"]
    payload_len = meta["payload_len"]
    random_mode = meta["random_mode"]
    total_bits_needed = (header_size + payload_len) * 8

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    all_bits = _extract_bits_random(
        cap=cap,
        bits_needed=total_bits_needed,
        scheme=scheme,
        random_mode=random_mode,
        stego_key=stego_key,
    )
    cap.release()

    all_bytes = bits_to_bytes(all_bits)
    payload_raw = all_bytes[header_size: header_size + payload_len]

    if meta["encrypted"] and a51_key:
        payload_final = a51.decrypt_payload(a51_key, payload_raw)
    else:
        payload_final = payload_raw

    return {
        "payload": payload_final,
        "is_file": meta["is_file"],
        "filename": meta["filename"],
        "encrypted": meta["encrypted"],
        "random_mode": random_mode,
        "payload_len": payload_len,
    }
