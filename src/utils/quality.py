import math
import numpy as np

# Menghitung kualitas visual steganografi
def frame_psnr_mse(
    cover_frame: np.ndarray,
    stego_frame: np.ndarray,
    max_val: float = 255.0,
) -> tuple[float, float]:

    c = cover_frame.astype(np.float64)
    s = stego_frame.astype(np.float64)

    mse = float(np.mean((c - s) ** 2))

    if mse == 0.0:
        return float("inf"), 0.0

    psnr = 10.0 * math.log10((max_val ** 2) / mse)
    return psnr, mse

# Per-video
def compute_psnr_mse_frames(
    cover_frames: list,
    stego_frames: list,
) -> tuple[list[float], list[float]]:
    
# Hitung PSNR dan MSE untuk setiap pasangan frame.
    n = min(len(cover_frames), len(stego_frames))
    psnr_list: list[float] = []
    mse_list:  list[float] = []

    for i in range(n):
        psnr, mse = frame_psnr_mse(cover_frames[i], stego_frames[i])
        psnr_list.append(psnr)
        mse_list.append(mse)

    return psnr_list, mse_list

# Video-level summary from file paths
def video_quality_summary(cover_path: str, stego_path: str) -> dict:
    try:
        import cv2
    except ImportError as e:
        raise ImportError("opencv-python diperlukan untuk video_quality_summary.") from e

    cap_c = cv2.VideoCapture(cover_path)
    cap_s = cv2.VideoCapture(stego_path)

    psnr_list: list[float] = []
    mse_list:  list[float] = []

    while True:
        ret_c, fc = cap_c.read()
        ret_s, fs = cap_s.read()
        if not ret_c or not ret_s:
            break

        # OpenCV membaca BGR
        fc_f = fc.astype(np.float64)
        fs_f = fs.astype(np.float64)

        mse_val = float(np.mean((fc_f - fs_f) ** 2))
        if mse_val == 0.0:
            psnr_val = float("inf")
        else:
            psnr_val = 10.0 * math.log10((255.0 ** 2) / mse_val)

        psnr_list.append(psnr_val)
        mse_list.append(mse_val)

    cap_c.release()
    cap_s.release()

    finite_psnr = [p for p in psnr_list if p != float("inf")]
    n = len(psnr_list)

    return {
        "psnr_list": psnr_list,
        "mse_list":  mse_list,
        "psnr_avg":  float(np.mean(finite_psnr)) if finite_psnr else float("inf"),
        "psnr_min":  float(min(finite_psnr))      if finite_psnr else float("inf"),
        "psnr_max":  float(max(finite_psnr))      if finite_psnr else float("inf"),
        "mse_avg":   float(np.mean(mse_list))     if mse_list    else 0.0,
        "mse_max":   float(max(mse_list))          if mse_list    else 0.0,
        "n_frames":  n,
    }