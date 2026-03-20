import os
import cv2
import numpy as np

from .a51 import a51
from .lsb import (
    embed_to_video,
    extract_from_video,
    calculate_capacity,
    rgb_bits,
)

# Embed

def embed_message(
    cover_path: str,
    output_path: str,
    msg_type: str,
    msg_data: str,
    use_enc: bool,
    enc_key: str,
    insert_mode: str,
    stego_key: str,
    frame_sel: str = "All frames",
    frame_n: int = 50,
    r_bits: int = 3,
    g_bits: int = 3,
    b_bits: int = 2,
    progress_cb=None,
    log_cb=None,
) -> dict:
    """
    Embed pesan ke dalam video AVI lalu kembalikan dict hasil.

    Returns
    -------
    dict with keys: psnr, mse, frames, output, cover_frame, stego_frame
    """

    def _log(msg):
        if log_cb:
            log_cb(msg)

    def _progress(pct):
        if progress_cb:
            progress_cb(pct)

    scheme = rgb_bits((r_bits, g_bits, b_bits))

    # Baca payload 
    if msg_type == "text":
        payload   = msg_data.encode("utf-8")
        is_file   = False
        filename  = ""
    else:
        with open(msg_data, "rb") as f:
            payload = f.read()
        is_file  = True
        filename = os.path.basename(msg_data)

    _log(f"Payload size  : {len(payload):,} bytes")
    _log(f"Scheme LSB    : R={scheme[0]} G={scheme[1]} B={scheme[2]}")
    _log(f"Insert mode   : {insert_mode}")
    _log(f"Frame selection: {frame_sel}" + (f" (N={frame_n})" if frame_sel == "First N frames" else ""))
    _log(f"Encryption    : {'A5/1' if use_enc else 'None'}")

    # Kunci A5/1
    a51_key = None
    if use_enc:
        a51_key = a51.derive_key(enc_key)
        _log("A5/1 key derived (SHA-256 → 64-bit)")

    _progress(5)

    # Kapasitas
    cap = calculate_capacity(cover_path, scheme)
    _log(f"Video capacity: {cap:,} bytes")

    _progress(10)

    # Embed
    _log("Embedding…")
    mse_list, psnr_list, mse_avg, psnr_avg = embed_to_video(
        cover_path   = cover_path,
        output_path  = output_path,
        payload      = payload,
        is_file      = is_file,
        filename     = filename,
        encrypt      = use_enc,
        a51_key      = a51_key,
        random_mode  = (insert_mode == "random"),
        stego_key    = stego_key,
        scheme       = scheme,
    )

    _progress(90)

    # Ambil frame pertama untuk histogram
    cover_frame = _read_first_frame_rgb(cover_path)
    stego_frame = _read_first_frame_rgb(output_path)

    _progress(100)
    _log(f"Done! PSNR avg={psnr_avg:.2f} dB  MSE avg={mse_avg:.4f}")

    return {
        "psnr":        psnr_avg,
        "mse":         mse_avg,
        "frames":      len(mse_list),
        "output":      output_path,
        "cover_frame": cover_frame,
        "stego_frame": stego_frame,
    }

# Extract

def extract_message(
    stego_path: str,
    use_dec: bool,
    dec_key: str,
    use_rand: bool,
    stego_key: str,
    progress_cb=None,
    log_cb=None,
) -> dict:
    """
    Ekstrak pesan dari stego-video AVI.

    Returns
    -------
    dict with keys: data, meta, psnr, mse, frames
    """

    def _log(msg):
        if log_cb:
            log_cb(msg)

    def _progress(pct):
        if progress_cb:
            progress_cb(pct)

    _log(f"Loading stego-video: {os.path.basename(stego_path)}")
    _progress(5)

    # Kunci A5/1
    a51_key = None
    if use_dec:
        a51_key = a51.derive_key(dec_key)
        _log("A5/1 key derived (SHA-256 → 64-bit)")

    _progress(10)

    # Ekstraksi
    _log("Extracting bits…")
    result = extract_from_video(
        stego_path = stego_path,
        a51_key    = a51_key,
        stego_key  = stego_key if use_rand else "",
    )

    _progress(85)

    payload  = result["payload"]
    is_file  = result["is_file"]
    filename = result["filename"]
    r        = result.get("r_bits", 3)
    g        = result.get("g_bits", 3)
    b        = result.get("b_bits", 2)

    _log(f"Extracted {len(payload):,} bytes")
    _log(f"Type     : {'file' if is_file else 'text'}  |  filename: {filename}")
    _log(f"Scheme   : R={r} G={g} B={b}")

    # Hitung MSE/PSNR frame pertama saja (cepat)
    psnr_avg = 0.0
    mse_avg  = 0.0
    n_frames = 0
    try:
        from .lsb import calculate_video_mse_psnr
        # PSNR/MSE untuk extract hanya bisa jika cover tersedia
    except Exception:
        pass

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
        "psnr":   psnr_avg,
        "mse":    mse_avg,
        "frames": n_frames,
    }

# Helpers

def _read_first_frame_rgb(video_path: str):
    """Baca frame pertama video sebagai numpy array RGB (H,W,3) uint8."""
    cap = cv2.VideoCapture(video_path)
    ok, frame_bgr = cap.read()
    cap.release()
    if not ok or frame_bgr is None:
        return None
    return cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)