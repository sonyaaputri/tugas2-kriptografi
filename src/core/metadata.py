"""
metadata.py (NANTI AKU HAPUS KOMEN NYA, PERLU:D)
===========
Modul untuk encoding dan decoding metadata yang disisipkan ke dalam stego-video.

Struktur header binary (little-endian):
  [4  bytes]  magic          : b'SGAV'
  [1  byte]   msg_type       : 0 = text, 1 = file
  [1  byte]   flags          : bit0 = encrypted, bit1 = random_mode
  [1  byte]   lsb_config     : bit7-5 = r_bits (1-4), bit4-2 = g_bits (1-4), bit1-0 = b_bits-1 (0-3)
  [2  bytes]  ext_len        : panjang extension string dalam bytes
  [N  bytes]  ext            : extension string UTF-8 (misal ".pdf"), tanpa null-terminator
  [2  bytes]  filename_len   : panjang nama file dalam bytes
  [M  bytes]  filename       : nama file UTF-8
  [4  bytes]  payload_size   : ukuran payload dalam bytes (sesudah enkripsi jika ada)
  [32 bytes]  orig_md5       : MD5 hex digest pesan ASLI sebelum enkripsi (ASCII)
  [64 bytes]  orig_sha256    : SHA-256 hex digest pesan ASLI sebelum enkripsi (ASCII)
  ──────────────────────────────────────────────────────────────
  Total: 4+1+1+1+2+N+2+M+4+32+64 = 111 bytes + len(ext) + len(filename)

Catatan penting:
- Kunci enkripsi A5/1 dan stego-key TIDAK disimpan di sini (sesuai ketentuan tugas).
- Field lsb_config menyimpan r/g/b bits agar ekstraksi bisa pakai skema LSB yang sama.
"""

import struct
import hashlib

MAGIC = b'SGAV'

# Ukuran bagian tetap header (tidak termasuk ext dan filename yang variadik)
_FIXED_SIZE = (
    4  +  # magic
    1  +  # msg_type
    1  +  # flags
    1  +  # lsb_config
    2  +  # ext_len
    2  +  # filename_len
    4  +  # payload_size
    32 +  # orig_md5
    64    # orig_sha256
)  # = 111 bytes


# ─────────────────────────────────────────────────────────────────────────────
# Helper hash
# ─────────────────────────────────────────────────────────────────────────────
# CATATAN: Jika utils/integrity.py sudah mendefinisikan compute_hashes,
# hapus fungsi ini dan ganti dengan: from utils.integrity import compute_hashes

def compute_hashes(data: bytes) -> tuple[str, str]:
    """
    Menghitung MD5 dan SHA-256 dari data.

    Returns
    -------
    (md5_hex, sha256_hex) — keduanya lowercase hex string
    """
    md5    = hashlib.md5(data).hexdigest()     # selalu 32 karakter
    sha256 = hashlib.sha256(data).hexdigest()  # selalu 64 karakter
    return md5, sha256


# ─────────────────────────────────────────────────────────────────────────────
# LSB config byte helpers (internal)
# ─────────────────────────────────────────────────────────────────────────────

def _encode_lsb_config(r_bits: int, g_bits: int, b_bits: int) -> int:
    """
    Mengkodekan konfigurasi R/G/B bits ke dalam 1 byte.

    Layout:
      bit 7-5 : r_bits (1–4, disimpan langsung, 3 bit)
      bit 4-2 : g_bits (1–4, disimpan langsung, 3 bit)
      bit 1-0 : b_bits - 1 (0–3, karena b_bits range 1–4)

    Contoh: r=3, g=3, b=2  →  011 011 01  →  0x6D
    """
    if not (1 <= r_bits <= 4):
        raise ValueError(f"r_bits harus 1–4, dapat: {r_bits}")
    if not (1 <= g_bits <= 4):
        raise ValueError(f"g_bits harus 1–4, dapat: {g_bits}")
    if not (1 <= b_bits <= 4):
        raise ValueError(f"b_bits harus 1–4, dapat: {b_bits}")
    return (r_bits << 5) | (g_bits << 2) | (b_bits - 1)


def _decode_lsb_config(config_byte: int) -> tuple[int, int, int]:
    """
    Mendekodekan 1 byte config menjadi (r_bits, g_bits, b_bits).

    Raises ValueError jika nilai di luar range yang valid.
    """
    r_bits = (config_byte >> 5) & 0b111
    g_bits = (config_byte >> 2) & 0b111
    b_bits = (config_byte & 0b11) + 1
    if not (1 <= r_bits <= 4 and 1 <= g_bits <= 4 and 1 <= b_bits <= 4):
        raise ValueError(
            f"lsb_config byte tidak valid: 0x{config_byte:02X} "
            f"(r={r_bits}, g={g_bits}, b={b_bits}). "
            "Pastikan stego-video dibuat oleh StegoAVI."
        )
    return r_bits, g_bits, b_bits


# ─────────────────────────────────────────────────────────────────────────────
# Encode metadata → bytes
# ─────────────────────────────────────────────────────────────────────────────

def encode_metadata(
    msg_type: str,        # "text" atau "file"
    payload_size: int,    # ukuran payload bytes sesudah enkripsi (jika ada)
    encrypted: bool,
    insert_mode: str,     # "sequential" atau "random"
    r_bits: int,          # konfigurasi LSB channel R (1–4)
    g_bits: int,          # konfigurasi LSB channel G (1–4)
    b_bits: int,          # konfigurasi LSB channel B (1–4)
    orig_data: bytes,     # pesan ASLI sebelum enkripsi — untuk menghitung hash
    filename: str = "",   # nama file asli; kosong jika pesan teks
    ext: str = "",        # ekstensi termasuk titik, misal ".pdf"; kosong jika teks
) -> bytes:
    """
    Membuat bytes header metadata yang akan disisipkan sebelum payload utama.

    Returns
    -------
    bytes — header siap sisip
    """
    type_byte  = 0 if msg_type == "text" else 1
    lsb_config = _encode_lsb_config(r_bits, g_bits, b_bits)

    flags = 0
    if encrypted:
        flags |= 0b00000001
    if insert_mode == "random":
        flags |= 0b00000010

    ext_bytes      = ext.encode("utf-8")
    filename_bytes = filename.encode("utf-8")

    if len(ext_bytes) > 65535:
        raise ValueError("Extension string terlalu panjang (maks 65535 bytes)")
    if len(filename_bytes) > 65535:
        raise ValueError("Nama file terlalu panjang (maks 65535 bytes)")
    if payload_size > 0xFFFFFFFF:
        raise ValueError("Payload terlalu besar (maks ~4 GB)")

    md5_hex, sha256_hex = compute_hashes(orig_data)

    header = (
        MAGIC
        + struct.pack("<B", type_byte)
        + struct.pack("<B", flags)
        + struct.pack("<B", lsb_config)
        + struct.pack("<H", len(ext_bytes))
        + ext_bytes
        + struct.pack("<H", len(filename_bytes))
        + filename_bytes
        + struct.pack("<I", payload_size)
        + md5_hex.encode("ascii")     # tepat 32 bytes
        + sha256_hex.encode("ascii")  # tepat 64 bytes
    )
    return header


# ─────────────────────────────────────────────────────────────────────────────
# Decode bytes → dict metadata
# ─────────────────────────────────────────────────────────────────────────────

def decode_metadata(data: bytes) -> tuple[dict, int]:
    """
    Mem-parsing bytes header metadata yang diekstrak dari stego-video.

    Parameters
    ----------
    data : bytes mentah hasil ekstraksi dari stego-video,
           dimulai dari byte pertama (magic number).

    Returns
    -------
    (meta, header_size)
      meta        : dict semua field metadata
      header_size : jumlah bytes yang dikonsumsi header;
                    payload asli ada di posisi data[header_size:]

    Raises
    ------
    ValueError   jika magic tidak cocok, data terpotong, atau config invalid.
    struct.error jika data terlalu pendek untuk di-unpack.
    """
    offset = 0

    # ── magic ──────────────────────────────────────────────────────────────
    if len(data) < 4:
        raise ValueError("Data terlalu pendek untuk header StegoAVI.")
    if data[offset:offset + 4] != MAGIC:
        raise ValueError(
            f"Magic number tidak cocok. "
            f"Ditemukan {data[offset:offset+4]!r}, expected {MAGIC!r}. "
            "Pastikan file adalah stego-video yang valid."
        )
    offset += 4

    # ── msg_type ───────────────────────────────────────────────────────────
    type_byte = struct.unpack_from("<B", data, offset)[0]
    offset += 1
    msg_type = "text" if type_byte == 0 else "file"

    # ── flags ──────────────────────────────────────────────────────────────
    flags = struct.unpack_from("<B", data, offset)[0]
    offset += 1
    encrypted   = bool(flags & 0b00000001)
    insert_mode = "random" if (flags & 0b00000010) else "sequential"

    # ── lsb_config ─────────────────────────────────────────────────────────
    config_byte        = struct.unpack_from("<B", data, offset)[0]
    offset += 1
    r_bits, g_bits, b_bits = _decode_lsb_config(config_byte)

    # ── ext ────────────────────────────────────────────────────────────────
    ext_len = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    ext = data[offset:offset + ext_len].decode("utf-8")
    offset += ext_len

    # ── filename ───────────────────────────────────────────────────────────
    filename_len = struct.unpack_from("<H", data, offset)[0]
    offset += 2
    filename = data[offset:offset + filename_len].decode("utf-8")
    offset += filename_len

    # ── payload_size ───────────────────────────────────────────────────────
    payload_size = struct.unpack_from("<I", data, offset)[0]
    offset += 4

    # ── hashes ─────────────────────────────────────────────────────────────
    orig_md5    = data[offset:offset + 32].decode("ascii")
    offset += 32
    orig_sha256 = data[offset:offset + 64].decode("ascii")
    offset += 64

    if not filename:
        filename = "message.txt" if msg_type == "text" else "extracted_file"

    meta = {
        "msg_type":    msg_type,
        "encrypted":   encrypted,
        "insert_mode": insert_mode,
        "r_bits":      r_bits,
        "g_bits":      g_bits,
        "b_bits":      b_bits,
        "ext":         ext,
        "filename":    filename,
        "size":        payload_size,
        "orig_md5":    orig_md5,
        "orig_sha256": orig_sha256,
    }
    return meta, offset


# ─────────────────────────────────────────────────────────────────────────────
# Utilitas
# ─────────────────────────────────────────────────────────────────────────────

def estimate_header_size(filename: str = "", ext: str = "") -> int:
    """
    Menghitung ukuran header dalam bytes untuk estimasi kapasitas sisip.
    Berguna sebelum proses embed dimulai.
    """
    return _FIXED_SIZE + len(ext.encode("utf-8")) + len(filename.encode("utf-8"))