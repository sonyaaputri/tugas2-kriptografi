import os
import cv2
import math
import random as _random

from .a51 import a51
from .lsb import (
    extract_from_video,
    calculate_capacity,
    rgb_bits,
    calculate_video_mse_psnr,
    bytes_to_bits,
    embed_bits_in_pixel,
)
from .metadata import encode_metadata


# Embed

def embed_message_mp4(
    cover_path: str,
    output_path: str,
    msg_type: str,
    msg_data: str,
    use_enc: bool,
    enc_key: str,
    insert_mode: str,
    stego_key: str,
    r_bits: int,
    g_bits: int,
    b_bits: int,
    progress_cb=None,
    log_cb=None,
) -> dict:
    """
    Embed pesan ke dalam video MP4.
    Menggunakan codec mp4v (MPEG-4 Part 2); kualitas tergantung implementasi OpenCV.

    Returns
    -------
    dict: psnr, mse, frames, output
    """

    def _log(msg):
        if log_cb:
            log_cb(msg)

    def _progress(pct):
        if progress_cb:
            progress_cb(pct)

    scheme = rgb_bits((r_bits, g_bits, b_bits))

    # Pastikan output berekstensi .mp4
    if not output_path.lower().endswith(".mp4"):
        output_path = os.path.splitext(output_path)[0] + ".mp4"

    # Baca payload
    if msg_type == "text":
        payload = msg_data.encode("utf-8")
        is_file = False
        filename = ""
    else:
        with open(msg_data, "rb") as f:
            payload = f.read()
        is_file = True
        filename = os.path.basename(msg_data)

    _log(f"[MP4] Payload  : {len(payload):,} bytes")
    _log(f"[MP4] Scheme   : R={scheme[0]} G={scheme[1]} B={scheme[2]}")
    _log("[MP4] PERINGATAN: MP4 bersifat lossy; integritas data tidak dijamin.")

    # Kunci A5/1
    a51_key = None
    if use_enc:
        a51_key = a51.derive_key(enc_key)
        _log("[MP4] A5/1 key derived")

    _progress(5)

    # Kapasitas
    cap_bytes = calculate_capacity(cover_path, scheme)
    _log(f"[MP4] Capacity : {cap_bytes:,} bytes")

    _progress(10)
    _log("[MP4] Embedding…")

    # Metadata video
    cap = cv2.VideoCapture(cover_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka video: {cover_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out_w = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out_w.isOpened():
        cap.release()
        raise ValueError("Gagal membuat output MP4 (codec mp4v tidak tersedia).")

    if use_enc and a51_key:
        payload_to_embed = a51.encrypt_payload(a51_key, payload)
    else:
        payload_to_embed = payload

    msg_type_str = "file" if is_file else "text"
    insert_mode_s = "random" if insert_mode == "random" else "sequential"

    ext = ""
    if is_file and filename:
        dot = filename.rfind(".")
        ext = filename[dot:] if dot != -1 else ""

    header = encode_metadata(
        msg_type=msg_type_str,
        payload_size=len(payload_to_embed),
        encrypted=use_enc,
        insert_mode=insert_mode_s,
        r_bits=scheme[0],
        g_bits=scheme[1],
        b_bits=scheme[2],
        orig_data=payload,
        filename=filename if is_file else "",
        ext=ext,
    )

    full_data = header + payload_to_embed
    if len(full_data) > cap_bytes:
        cap.release()
        out_w.release()
        raise ValueError(
            f"Data ({len(full_data)} bytes) melebihi kapasitas video ({cap_bytes} bytes)."
        )

    bits_per_pix = sum(scheme)
    header_bits = bytes_to_bits(header)
    payload_bits = bytes_to_bits(payload_to_embed)

    header_idx = 0
    payload_idx = 0
    done_header = False
    done_payload = False

    first_frame = True
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
    frame_no = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_no += 1
        h, w = frame.shape[:2]
        total_px = h * w
        frame_flat = frame.reshape(-1, 3)

        # 1) Header selalu sequential
        start_payload_idx = 0
        if not done_header:
            for pi in range(total_px):
                if header_idx >= len(header_bits):
                    done_header = True
                    start_payload_idx = pi
                    break

                chunk = header_bits[header_idx: header_idx + bits_per_pix]
                while len(chunk) < bits_per_pix:
                    chunk.append(0)

                r_new, g_new, b_new = embed_bits_in_pixel(
                    (frame_flat[pi][2], frame_flat[pi][1], frame_flat[pi][0]),
                    chunk,
                    scheme,
                )
                frame_flat[pi] = [b_new, g_new, r_new]
                header_idx += bits_per_pix

            if not done_header:
                # frame habis dipakai untuk header, belum boleh masuk payload
                out_w.write(frame_flat.reshape(h, w, 3))
                _progress(min(90, 10 + int(frame_no / total_frames * 80)))
                continue

        # 2) Payload mengikuti mode yang dipilih
        if not done_payload:
            if first_frame:
                available_indices = list(range(start_payload_idx, total_px))
                first_frame = False
            else:
                available_indices = list(range(total_px))

            if insert_mode_s == "random" and stego_key:
                rng = _random.Random(stego_key)
                rng.shuffle(available_indices)

            for pi in available_indices:
                if payload_idx >= len(payload_bits):
                    done_payload = True
                    break

                chunk = payload_bits[payload_idx: payload_idx + bits_per_pix]
                while len(chunk) < bits_per_pix:
                    chunk.append(0)

                r_new, g_new, b_new = embed_bits_in_pixel(
                    (frame_flat[pi][2], frame_flat[pi][1], frame_flat[pi][0]),
                    chunk,
                    scheme,
                )
                frame_flat[pi] = [b_new, g_new, r_new]
                payload_idx += bits_per_pix

        out_w.write(frame_flat.reshape(h, w, 3))
        _progress(min(90, 10 + int(frame_no / total_frames * 80)))

    cap.release()
    out_w.release()

    _progress(95)
    _log("[MP4] Embedding selesai")

    try:
        mse_avg, psnr_avg, n_frames = calculate_video_mse_psnr(cover_path, output_path)
    except Exception:
        mse_avg, psnr_avg, n_frames = 0.0, float("inf"), 0

    _progress(100)

    return {
        "psnr": psnr_avg,
        "mse": mse_avg,
        "frames": n_frames,
        "output": output_path,
    }


# Extract

def extract_message_mp4(
    stego_path: str,
    use_dec: bool,
    dec_key: str,
    use_rand: bool,
    stego_key: str,
    progress_cb=None,
    log_cb=None,
) -> dict:
    """
    Ekstrak pesan dari stego-video MP4.
    Antarmuka identik dengan avi_handler.extract_message.
    """

    def _log(msg):
        if log_cb:
            log_cb(msg)

    def _progress(pct):
        if progress_cb:
            progress_cb(pct)

    _log(f"[MP4] Loading: {os.path.basename(stego_path)}")
    _log("[MP4] PERINGATAN: MP4 lossy — hasil ekstraksi mungkin tidak sempurna.")
    _progress(5)

    a51_key = None
    if use_dec:
        a51_key = a51.derive_key(dec_key)
        _log("[MP4] A5/1 key derived")

    _progress(10)
    _log("[MP4] Extracting bits…")

    result = extract_from_video(
        stego_path=stego_path,
        a51_key=a51_key,
        stego_key=stego_key if use_rand else "",
    )

    _progress(90)

    payload = result["payload"]
    is_file = result["is_file"]
    filename = result["filename"]
    r = result.get("r_bits", 3)
    g = result.get("g_bits", 3)
    b = result.get("b_bits", 2)

    _log(f"[MP4] Extracted {len(payload):,} bytes")

    _progress(100)

    meta = {
        "msg_type": "file" if is_file else "text",
        "filename": filename,
        "size": len(payload),
        "encrypted": result["encrypted"],
        "insert_mode": "random" if result["random_mode"] else "sequential",
        "orig_md5": result.get("orig_md5", ""),
        "orig_sha256": result.get("orig_sha256", ""),
        "r_bits": r,
        "g_bits": g,
        "b_bits": b,
    }

    return {
        "data": payload,
        "meta": meta,
        "psnr": 0.0,
        "mse": 0.0,
        "frames": 0,
    }


# Helpers

def _read_first_frame_rgb(video_path: str):
    cap = cv2.VideoCapture(video_path)
    ok, frame_bgr = cap.read()
    cap.release()
    if not ok or frame_bgr is None:
        return None
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)