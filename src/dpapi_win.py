"""
Windows DPAPI (Data Protection API) helper for securing sensitive credentials like Sungur Admin Token.
Uses CryptProtectData / CryptUnprotectData to ensure credentials stored in registry (QSettings)
are encrypted with the user's Windows login credentials.
"""
import sys
import base64
from typing import Optional

def protect_secret(plaintext: Optional[str]) -> str:
    """Encrypts plaintext using Windows DPAPI (CurrentUser). Returns base64 string."""
    if not plaintext:
        return ""
    if sys.platform != "win32":
        return "b64:" + base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")

    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        data_bytes = plaintext.encode("utf-8")
        buf = ctypes.create_string_buffer(data_bytes)
        in_blob = DATA_BLOB(len(data_bytes), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()

        # CRYPTPROTECT_UI_FORBIDDEN = 0x01
        res = ctypes.windll.crypt32.CryptProtectData(
            ctypes.byref(in_blob),
            "SungurAdminToken",
            None,
            None,
            None,
            0x01,
            ctypes.byref(out_blob)
        )
        if not res:
            return None

        try:
            encrypted_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return "dpapi:" + base64.b64encode(encrypted_bytes).decode("utf-8")
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return None


def unprotect_secret(encrypted_text: Optional[str]) -> str:
    """Decrypts base64 DPAPI string. Returns original plaintext."""
    if not encrypted_text:
        return ""
    if encrypted_text.startswith("b64:"):
        try:
            return base64.b64decode(encrypted_text[4:]).decode("utf-8", errors="ignore")
        except Exception:
            return ""
    if not encrypted_text.startswith("dpapi:"):
        # Plaintext backward compatibility
        return encrypted_text
    if sys.platform != "win32":
        return ""

    try:
        import ctypes
        from ctypes import wintypes

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [
                ("cbData", wintypes.DWORD),
                ("pbData", ctypes.POINTER(ctypes.c_byte))
            ]

        raw_b64 = encrypted_text[6:]
        encrypted_bytes = base64.b64decode(raw_b64)
        buf = ctypes.create_string_buffer(encrypted_bytes)
        in_blob = DATA_BLOB(len(encrypted_bytes), ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte)))
        out_blob = DATA_BLOB()

        # CRYPTPROTECT_UI_FORBIDDEN = 0x01
        res = ctypes.windll.crypt32.CryptUnprotectData(
            ctypes.byref(in_blob),
            None,
            None,
            None,
            None,
            0x01,
            ctypes.byref(out_blob)
        )
        if not res:
            return ""
        try:
            decrypted_bytes = ctypes.string_at(out_blob.pbData, out_blob.cbData)
            return decrypted_bytes.decode("utf-8", errors="ignore")
        finally:
            ctypes.windll.kernel32.LocalFree(out_blob.pbData)
    except Exception:
        return ""
