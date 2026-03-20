import math
import os
import random
from typing import Iterable

import cv2
import numpy as np

from .a51 import a51
from .metadata import decode_metadata, encode_metadata, estimate_header_size


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

def _embed_bits_into_frames(
    cap: cv2.VideoCapture,
    out: cv2.VideoWriter,
    bit_stream: list[int],
    scheme: tuple[int, int, int],
    random_mode: bool = False,
    stego_key: str = "",
):
    bits_per_pixel = sum(scheme)
    bit_idx = 0
    total_bits = len(bit_stream)
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
                    (
                        frame_flat[pix_idx][2],
                        frame_flat[pix_idx][1],
                        frame_flat[pix_idx][0],
                    ),
                    chunk,
                    scheme,
                )
                frame_flat[pix_idx] = [b_new, g_new, r_new]
                bit_idx += bits_per_pixel

            frame = frame_flat.reshape(h, w, 3)

        out.write(frame)

    return bit_idx

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

    if encrypt and a51_key:
        payload_to_embed = a51.encrypt_payload(a51_key, payload)
    else:
        payload_to_embed = payload

    msg_type = "file" if is_file else "text"
    insert_mode = "random" if random_mode else "sequential"
    ext = ""
    if is_file and filename:
        dot = filename.rfind(".")
        ext = filename[dot:] if dot != -1 else ""

    header = encode_metadata(
        msg_type=msg_type,
        payload_size=len(payload_to_embed),
        encrypted=encrypt,
        insert_mode=insert_mode,
        r_bits=scheme[0],
        g_bits=scheme[1],
        b_bits=scheme[2],
        orig_data=payload,
        filename=filename if is_file else "",
        ext=ext,
    )

    full_data = header + payload_to_embed

    if not validate_capacity(cover_path, full_data, scheme):
        cap = calculate_capacity(cover_path, scheme)
        raise ValueError(
            f"Data ({len(full_data)} bytes) melebihi kapasitas video ({cap} bytes)."
        )

    cap = cv2.VideoCapture(cover_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka video: {cover_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"FFV1")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"HFYU")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    if not out.isOpened():
        cap.release()
        raise ValueError(
            "Gagal membuat AVI lossless. FFV1/HFYU tidak tersedia di sistem ini."
        )

    # Header selalu sequential agar extractor bisa bootstrap metadata
    header_bits = bytes_to_bits(header)
    _embed_bits_into_frames(
        cap=cap,
        out=out,
        bit_stream=header_bits,
        scheme=scheme,
        random_mode=False,
        stego_key="",
    )

    # Payload mengikuti mode yang dipilih
    cap.release()
    out.release()

    cap = cv2.VideoCapture(output_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka stego sementara: {output_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    temp_path = output_path + ".tmp.avi"
    fourcc = cv2.VideoWriter_fourcc(*"FFV1")
    out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

    if not out.isOpened():
        fourcc = cv2.VideoWriter_fourcc(*"HFYU")
        out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))

    if not out.isOpened():
        cap.release()
        raise ValueError(
            "Gagal membuat AVI lossless sementara. FFV1/HFYU tidak tersedia di sistem ini."
        )

    header_bits_len = len(header_bits)
    bits_per_pixel = sum(scheme)
    pixels_used_by_header = math.ceil(header_bits_len / bits_per_pixel)

    payload_bits = bytes_to_bits(payload_to_embed)

    first_frame = True
    payload_idx = 0
    done = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if not done:
            h, w = frame.shape[:2]
            total_pixels = h * w
            frame_flat = frame.reshape(-1, 3)

            if first_frame:
                available_indices = list(range(pixels_used_by_header, total_pixels))
                first_frame = False
            else:
                available_indices = list(range(total_pixels))

            if random_mode and stego_key:
                rng = random.Random(stego_key)
                rng.shuffle(available_indices)

            for pix_idx in available_indices:
                if payload_idx >= len(payload_bits):
                    done = True
                    break

                chunk = payload_bits[payload_idx: payload_idx + bits_per_pixel]
                while len(chunk) < bits_per_pixel:
                    chunk.append(0)

                r_new, g_new, b_new = embed_bits_in_pixel(
                    (
                        frame_flat[pix_idx][2],
                        frame_flat[pix_idx][1],
                        frame_flat[pix_idx][0],
                    ),
                    chunk,
                    scheme,
                )
                frame_flat[pix_idx] = [b_new, g_new, r_new]
                payload_idx += bits_per_pixel

            frame = frame_flat.reshape(h, w, 3)

        out.write(frame)

    cap.release()
    out.release()

    os.replace(temp_path, output_path)

    return calculate_video_mse_psnr(cover_path, output_path)


def _extract_bits_random(
    cap: cv2.VideoCapture,
    bits_needed: int,
    scheme: tuple[int, int, int],
    random_mode: bool,
    stego_key: str,
    skip_pixels_first_frame: int = 0,
    ):
    extracted_bits = []
    first_frame = True

    while len(extracted_bits) < bits_needed:
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        total_pix = h * w
        frame_flat = frame.reshape(-1, 3)

        if first_frame and skip_pixels_first_frame > 0:
            pixel_indices = list(range(skip_pixels_first_frame, total_pix))
            first_frame = False
        else:
            pixel_indices = list(range(total_pix))
            first_frame = False

        if random_mode and stego_key:
            rng = random.Random(stego_key)
            rng.shuffle(pixel_indices)

        for pix_idx in pixel_indices:
            bits = extract_bits_from_pixel(
                (
                    frame_flat[pix_idx][2],
                    frame_flat[pix_idx][1],
                    frame_flat[pix_idx][0],
                ),
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

    max_header_bytes = estimate_header_size() + 1024
    bits_needed_header = max_header_bytes * 8

    header_bits = _extract_bits_random(
        cap=cap,
        bits_needed=bits_needed_header,
        scheme=scheme,
        random_mode=False,
        stego_key="",
        skip_pixels_first_frame=0,
    )
    header_bytes = bits_to_bytes(header_bits[:bits_needed_header])
    meta, header_size = decode_metadata(header_bytes)

    payload_len = meta["size"]
    random_mode = meta["insert_mode"] == "random"

    bits_per_pixel = sum(scheme)
    header_bits_len = header_size * 8
    pixels_used_by_header = math.ceil(header_bits_len / bits_per_pixel)
    payload_bits_needed = payload_len * 8

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    payload_bits = _extract_bits_random(
        cap=cap,
        bits_needed=payload_bits_needed,
        scheme=scheme,
        random_mode=random_mode,
        stego_key=stego_key,
        skip_pixels_first_frame=pixels_used_by_header,
    )
    cap.release()

    payload_raw = bits_to_bytes(payload_bits)[:payload_len]

    if meta["encrypted"] and a51_key:
        payload_final = a51.decrypt_payload(a51_key, payload_raw)
    else:
        payload_final = payload_raw

    return {
        "payload": payload_final,
        "is_file": meta["msg_type"] == "file",
        "filename": meta["filename"],
        "encrypted": meta["encrypted"],
        "random_mode": random_mode,
        "payload_len": payload_len,
        "orig_md5": meta.get("orig_md5", ""),
        "orig_sha256": meta.get("orig_sha256", ""),
        "r_bits": meta.get("r_bits", scheme[0]),
        "g_bits": meta.get("g_bits", scheme[1]),
        "b_bits": meta.get("b_bits", scheme[2]),
    }