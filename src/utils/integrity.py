import hashlib
import os

# Hitung MD5 dan SHA-256 dari data bytes
def compute_hashes(data: bytes) -> tuple[str, str]:
    md5    = hashlib.md5(data).hexdigest()
    sha256 = hashlib.sha256(data).hexdigest()
    return md5, sha256


def compute_md5(data: bytes) -> str:
    """Hitung MD5 dari data bytes, kembalikan hex string 32 karakter."""
    return hashlib.md5(data).hexdigest()


def compute_sha256(data: bytes) -> str:
    """Hitung SHA-256 dari data bytes, kembalikan hex string 64 karakter."""
    return hashlib.sha256(data).hexdigest()


# Verification
def verify_md5(data: bytes, expected: str) -> bool:
    return compute_md5(data) == expected.lower().strip()


def verify_sha256(data: bytes, expected: str) -> bool:
    return compute_sha256(data) == expected.lower().strip()

# File-level helpers
def hash_file(path: str) -> tuple[str, str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"File tidak ditemukan: {path}")

    md5_h    = hashlib.md5()
    sha256_h = hashlib.sha256()

    with open(path, "rb") as f:
        while chunk := f.read(65536):
            md5_h.update(chunk)
            sha256_h.update(chunk)

    return md5_h.hexdigest(), sha256_h.hexdigest()

# Integrity report
def integrity_report(original: bytes, extracted: bytes) -> dict:
    orig_md5,  orig_sha256 = compute_hashes(original)
    ext_md5,   ext_sha256  = compute_hashes(extracted)

    md5_match    = (orig_md5    == ext_md5)
    sha256_match = (orig_sha256 == ext_sha256)

    return {
        "orig_md5":       orig_md5,
        "orig_sha256":    orig_sha256,
        "ext_md5":        ext_md5,
        "ext_sha256":     ext_sha256,
        "md5_match":      md5_match,
        "sha256_match":   sha256_match,
        "intact":         md5_match and sha256_match,
        "size_orig":      len(original),
        "size_extracted": len(extracted),
    }