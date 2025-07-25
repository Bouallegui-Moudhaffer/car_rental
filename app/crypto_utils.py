import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import os

SECRET_KEY = os.getenv("AES_SECRET_KEY", "1234567890123456").encode("utf-8")

def pad(text):
    pad_len = 16 - (len(text.encode('utf-8')) % 16)
    return text.encode('utf-8') + bytes([pad_len] * pad_len)

def unpad(padded_text):
    pad_len = padded_text[-1]
    return padded_text[:-pad_len]

def encrypt_answer(answer, key=SECRET_KEY):
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(answer))
    return base64.b64encode(iv + ciphertext).decode("utf-8")

def decrypt_answer(enc_data, key=SECRET_KEY):
    try:
        raw = base64.b64decode(enc_data)
        iv = raw[:16]
        ciphertext = raw[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted = cipher.decrypt(ciphertext)
        return unpad(decrypted).decode("utf-8")
    except Exception as e:
        return ""

