import os
import cv2
import numpy as np

from .a51 import a51
from .lsb import (
    embed_to_video,
    extract_from_video,
    calculate_capacity,
    rgb_bits,
    calculate_video_mse_psnr,
)

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
    dict: psnr, mse, frames, output, cover_frame, stego_frame
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
        payload  = msg_data.encode("utf-8")
        is_file  = False
        filename = ""
    else:
        with open(msg_data, "rb") as f:
            payload = f.read()
        is_file  = True
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

    # Embed menggunakan lsb.embed_to_video dengan fourcc mp4v
    _log("[MP4] Embedding…")

    # Buka cover untuk metadata video
    cap = cv2.VideoCapture(cover_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka video: {cover_path}")
    fps    = cap.get(cv2.CAP_PROP_FPS)
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Karena embed_to_video menggunakan XVID secara internal, buat wrapper yang menulis langsung mp4v.

    from .metadata import encode_metadata, estimate_header_size
    from .lsb import bytes_to_bits, bits_to_bytes, embed_bits_in_pixel
    import random as _random

    if use_enc and a51_key:
        payload_to_embed = a51.encrypt_payload(a51_key, payload)
    else:
        payload_to_embed = payload

    msg_type_str  = "file" if is_file else "text"
    insert_mode_s = "random" if insert_mode == "random" else "sequential"
    ext = ""
    if is_file and filename:
        dot = filename.rfind(".")
        ext = filename[dot:] if dot != -1 else ""

    header = encode_metadata(
        msg_type    = msg_type_str,
        payload_size= len(payload_to_embed),
        encrypted   = use_enc,
        insert_mode = insert_mode_s,
        r_bits      = scheme[0],
        g_bits      = scheme[1],
        b_bits      = scheme[2],
        orig_data   = payload,
        filename    = filename if is_file else "",
        ext         = ext,
    )
    full_data = header + payload_to_embed

    if len(full_data) > cap_bytes:
        raise ValueError(
            f"Data ({len(full_data)} bytes) melebihi kapasitas video ({cap_bytes} bytes)."
        )

    bit_stream   = bytes_to_bits(full_data)
    total_bits   = len(bit_stream)
    bits_per_pix = sum(scheme)

    cap_in  = cv2.VideoCapture(cover_path)
    fourcc  = cv2.VideoWriter_fourcc(*"mp4v")
    out_w   = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    bit_idx = 0
    done    = False

    while True:
        ret, frame = cap_in.read()
        if not ret:
            break

        if not done:
            h, w     = frame.shape[:2]
            total_px = h * w

            if insert_mode == "random" and stego_key:
                px_idx = list(range(total_px))
                rng    = _random.Random(stego_key)
                rng.shuffle(px_idx)
            else:
                px_idx = list(range(total_px))

            frame_flat = frame.reshape(-1, 3)

            for pi in px_idx:
                if bit_idx >= total_bits:
                    done = True
                    break
                chunk = bit_stream[bit_idx: bit_idx + bits_per_pix]
                while len(chunk) < bits_per_pix:
                    chunk.append(0)
                r_new, g_new, b_new = embed_bits_in_pixel(
                    (frame_flat[pi][2], frame_flat[pi][1], frame_flat[pi][0]),
                    chunk, scheme)
                frame_flat[pi] = [b_new, g_new, r_new]
                bit_idx += bits_per_pix

            frame = frame_flat.reshape(h, w, 3)

        out_w.write(frame)

    cap_in.release()
    out_w.release()

    _progress(85)

    mse_list, psnr_list, mse_avg, psnr_avg = calculate_video_mse_psnr(cover_path, output_path)

    cover_frame = _read_first_frame_rgb(cover_path)
    stego_frame = _read_first_frame_rgb(output_path)

    _progress(100)
    _log(f"[MP4] Done! PSNR={psnr_avg:.2f} dB  MSE={mse_avg:.4f}")

    return {
        "psnr":        psnr_avg,
        "mse":         mse_avg,
        "frames":      len(mse_list),
        "output":      output_path,
        "cover_frame": cover_frame,
        "stego_frame": stego_frame,
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
        stego_path = stego_path,
        a51_key    = a51_key,
        stego_key  = stego_key if use_rand else "",
    )

    _progress(90)

    payload  = result["payload"]
    is_file  = result["is_file"]
    filename = result["filename"]
    r = result.get("r_bits", 3)
    g = result.get("g_bits", 3)
    b = result.get("b_bits", 2)

    _log(f"[MP4] Extracted {len(payload):,} bytes")

    _progress(100)

    meta = {
        "msg_type":    "file" if is_file else "text",
        "filename":    filename,
        "size":        len(payload),
        "encrypted":   result["encrypted"],
        "insert_mode": "random" if result["random_mode"] else "sequential",
        "orig_md5":    result.get("orig_md5", ""),
        "orig_sha256": result.get("orig_sha256", ""),
        "r_bits": r, "g_bits": g, "b_bits": b,
    }

    return {
        "data":   payload,
        "meta":   meta,
        "psnr":   0.0,
        "mse":    0.0,
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