import os
import cv2

# Menghitungan kapasitas sisip video
def compute_capacity(video_path: str, bpp: int) -> tuple[int, int]:

    if not os.path.exists(video_path):
        return 0, 0

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0, 0

    total_pixels = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        total_pixels += h * w

    cap.release()

    cap_bits  = total_pixels * bpp
    cap_bytes = cap_bits // 8
    return cap_bytes, 0

#  Cek apakah payload muat di dalam video dengan skema bpp
def payload_fits(video_path: str, payload_size: int, bpp: int) -> bool:
    cap_bytes, _ = compute_capacity(video_path, bpp)
    return payload_size <= cap_bytes


def capacity_summary(video_path: str, bpp: int) -> str:
    cap_bytes, _ = compute_capacity(video_path, bpp)
    cap_mb = cap_bytes / 1_048_576
    return f"Capacity: {cap_mb:.2f} MB  (bpp={bpp})"