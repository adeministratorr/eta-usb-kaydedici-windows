import base64
import os
import re
from io import BytesIO
from typing import Tuple

def generate_otp_secret(length_bytes: int = 10) -> str:
    """
    Generates a cryptographically secure 16-character RFC 6238 Base32 secret key.
    10 bytes * 8 / 5 = 16 Base32 characters.
    """
    random_bytes = os.urandom(length_bytes)
    secret = base64.b32encode(random_bytes).decode("ascii")
    # Base32 standard: A-Z and 2-7
    return secret.strip().upper()

def get_otp_auth_url(username: str, secret: str, issuer: str = "pardus-etap") -> str:
    """
    Generates standard otpauth URI compatible with Google Authenticator, Stratum, FreeOTP.
    Format: otpauth://totp/USER@etap?secret=...&issuer=pardus-etap
    """
    clean_user = username.strip()
    clean_secret = secret.strip().upper()
    return f"otpauth://totp/{clean_user}@etap?secret={clean_secret}&issuer={issuer}&algorithm=SHA1&digits=6&period=30"

def generate_qr_image(otp_url: str):
    """
    Generates a QPixmap or PNG bytes for the given OTP URL.
    Returns (QPixmap, error_message).
    """
    try:
        from PySide6.QtGui import QPixmap, QImage
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(otp_url)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        pix = QPixmap()
        pix.loadFromData(buffer.getvalue(), "PNG")
        return pix, None
    except ImportError:
        # Fallback if qrcode package is missing: Return None and error
        return None, "qrcode kütüphanesi eksik (pip install qrcode pillow)."
    except Exception as e:
        return None, str(e)
