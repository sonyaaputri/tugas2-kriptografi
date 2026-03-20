import os
import cv2
import numpy as np

# embed_message

def embed_message(
    cover_path: str,
    output_path: str,
    msg_type: str,
    msg_data: str,
    use_enc: bool,
    enc_key: str,
    insert_mode: str,
    stego_key: str,
    frame_sel: str,
    frame_n: int,
    r_bits: int,
    g_bits: int,
    b_bits: int,
    progress_cb=None,
    log_cb=None,
) -> dict:
    """
    Pilih handler yang sesuai berdasarkan ekstensi cover_path,
    lalu delegasikan ke avi_handler atau mp4_handler.

    Parameters
    ----------
    Semua parameter sama dengan EmbedTab._embed_worker.

    Returns
    -------
    dict: psnr, mse, frames, output, cover_frame, stego_frame
    """
    ext = os.path.splitext(cover_path)[1].lower()

    common = dict(
        cover_path  = cover_path,
        output_path = output_path,
        msg_type    = msg_type,
        msg_data    = msg_data,
        use_enc     = use_enc,
        enc_key     = enc_key,
        insert_mode = insert_mode,
        stego_key   = stego_key,
        r_bits      = r_bits,
        g_bits      = g_bits,
        b_bits      = b_bits,
        progress_cb = progress_cb,
        log_cb      = log_cb,
    )

    if ext == ".mp4":
        from .mp4_handler import embed_message_mp4
        return embed_message_mp4(**common)
    else:
        # Default: AVI (atau format lain yang bisa dibaca OpenCV)
        from .avi_handler import embed_message
        return embed_message(**common)

# load_frames

def load_frames(video_path: str) -> list:
    """
    Baca semua frame dari video dan kembalikan sebagai list numpy array RGB.

    Digunakan oleh CompareTab untuk analisis histogram dan PSNR/MSE.

    Parameters
    ----------
    video_path : str   path ke berkas video (AVI/MP4)

    Returns
    -------
    list[np.ndarray]   setiap elemen berukuran (H, W, 3) uint8, color order RGB
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Gagal membuka video: {video_path}")

    frames = []
    while True:
        ret, frame_bgr = cap.read()
        if not ret:
            break
        # Konversi BGR → RGB agar konsisten dengan matplotlib & histogram widget
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        frames.append(frame_rgb)

    cap.release()
    return frames