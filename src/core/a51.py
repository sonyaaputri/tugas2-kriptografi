import hashlib
import math

class a51:
    def __init__(self):
        #inisiasi panjang register
        self.len_r1 = 19
        self.len_r2 = 22
        self.len_r3 = 23

        #posisi tap
        self.tap_r1 = [13, 16, 17, 18]
        self.tap_r2 = [20, 21]
        self.tap_r3 = [7, 20, 21, 22]

        #posisi clocking bit
        self.cb_r1 = 8
        self.cb_r2 = 10
        self.cb_r3 = 10

        self.r1 = [0] * self.len_r1
        self.r2 = [0] * self.len_r2
        self.r3 = [0] * self.len_r3

    def key_setup(self, key_bits: list[int], frame_bits: list[int]):

        self.r1 = [0] * self.len_r1
        self.r2 = [0] * self.len_r2
        self.r3 = [0] * self.len_r3

        #session key 64 siklus
        for key_bit in key_bits:
            self.clock()
            self.r1[0] = self.r1[0] ^ key_bit
            self.r2[0] = self.r2[0] ^ key_bit
            self.r3[0] = self.r3[0] ^ key_bit

        #frame number 22 siklus
        for bit in frame_bits:
            self.clock()
            self.r1[0] = self.r1[0] ^ bit
            self.r2[0] = self.r2[0] ^ bit
            self.r3[0] = self.r3[0] ^ bit

        for _ in range(100):
            self.clock_majority()


    def shift_reg(self, reg: list, tap: list):
        feedback = 0
        for t in tap:
            feedback ^= reg[t]

        #geser ke kanan
        new_reg = [feedback] + reg[:-1]
        return new_reg
    
    def majority(self):
        bits = [
            self.r1[self.cb_r1],
            self.r2[self.cb_r2],
            self.r3[self.cb_r3]
        ]
        return 1 if sum(bits) >= 2 else 0
    
    def clock_majority(self):
        majority = self.majority()
        if majority == self.r1[self.cb_r1]:
            self.r1 = self.shift_reg(self.r1, self.tap_r1)
        if majority == self.r2[self.cb_r2]:
            self.r2 = self.shift_reg(self.r2, self.tap_r2)
        if majority == self.r3[self.cb_r3]:
            self.r3 = self.shift_reg(self.r3, self.tap_r3)

        return self.r1[0] ^ self.r2[0] ^ self.r3[0]
    
    def clock(self):
        self.r1 = self.shift_reg(self.r1, self.tap_r1)
        self.r2 = self.shift_reg(self.r2, self.tap_r2)
        self.r3 = self.shift_reg(self.r3, self.tap_r3)

    def generate_keystream(self, length: int):
        keystream = []
        for _ in range(length):
            keystream.append(self.clock_majority())
        return keystream

    @staticmethod
    def bytes_to_bits(data: bytes):
        bits = []
        for byte in data:
            for i in range(7, -1, -1):
                bits.append((byte >> i) & 1)
        return bits

    @staticmethod
    def bits_to_bytes(bits: list[int]):
        result = []
        for i in range(0, len(bits), 8):
            byte = 0
            for b in bits[i:i + 8]:
                byte = (byte << 1) | b
            result.append(byte)
        return bytes(result)

    @staticmethod
    def encrypt_payload(key: bytes, payload: bytes):
        block_size = 228

        key_bits = a51.bytes_to_bits(key)
        payload_bits = a51.bytes_to_bits(payload)

        cipher = a51()
        encrypted_bits = []

        if not payload_bits:
            return b""

        num_blocks = math.ceil(len(payload_bits) / block_size)

        for block_idx in range(num_blocks):
            start = block_idx * block_size
            end = min(start + block_size, len(payload_bits))
            block = payload_bits[start:end]

            fn_bits = [(block_idx >> (21 - i)) & 1 for i in range(22)]
            cipher.key_setup(key_bits, fn_bits)

            keystream = cipher.generate_keystream(len(block))
            encrypted_block = [p ^ k for p, k in zip(block, keystream)]
            encrypted_bits.extend(encrypted_block)

        return a51.bits_to_bytes(encrypted_bits)

    @staticmethod
    def decrypt_payload(key: bytes, ciphertext: bytes):
        return a51.encrypt_payload(key, ciphertext)

    @staticmethod
    def derive_key(user_key: str):
        #Ubah key string menjadi 64 bit menggunakan SHA-256
        hash_bytes = hashlib.sha256(user_key.encode()).digest()
        return hash_bytes[:8]  #