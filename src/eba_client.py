"""EBA sunucu istekleri. Referans: MainWindow.py 2.0.6 (satir 134-348)
+ 1.0.10 (satir 516-542). Sira ayni: sifre -> kayit.

Hatalar (baslik, mesaj, aksiyon) + ham detay doner; UI secim yapar.
"""

import requests

from eba_errors import (
    EBA_DELETE_USB_URL,
    EBA_ORIGIN,
    EBA_PASSWORD_RESET_URL,
    EBA_REGISTER_USB_URL,
    GENERIC_DELETE,
    GENERIC_REGISTER,
    NO_CONNECTION,
    lookup,
    parse_result_code,
)

TIMEOUT = 15


def _headers():
    return {"origin": EBA_ORIGIN}


def new_session():
    """Akis-local baglanti havuzu. Her worker kendi Session'ini acar/kapatir;
    global paylasim yok (requests.Session thread-safe degil)."""
    s = requests.Session()
    s.headers.update(_headers())
    return s


def _http_get(url, timeout, session=None, **kw):
    if session is not None:
        return session.get(url, timeout=timeout, **kw)
    return requests.get(url, timeout=timeout, **kw)


def _http_post(url, timeout, session=None, **kw):
    if session is not None:
        return session.post(url, timeout=timeout, **kw)
    return requests.post(url, timeout=timeout, **kw)


def get_teacher_info(info_url, timeout=TIMEOUT, session=None):
    """Token redirect URL'sinden ogretmen bilgisi. (ok, data|hata)."""
    try:
        r = _http_get(info_url, timeout=timeout, session=session)
    except Exception as e:
        return False, {"title": NO_CONNECTION[0], "message": NO_CONNECTION[1],
                       "action": NO_CONNECTION[2], "detail": str(e)}
    if r.status_code != 200:
        return False, {"title": "EBA'ya ulaşılamadı",
                       "message": "EBA hatalı kod döndürdü.",
                       "action": "Tekrar deneyin.",
                       "detail": f"HTTP {r.status_code}: {(r.text or '')[:300]}"}
    try:
        obj = r.json()
    except Exception as e:
        return False, {"title": "EBA cevabı bozuk",
                       "message": "EBA'dan gelen bilgi okunamadı.",
                       "action": "Yeniden giriş yapın.",
                       "detail": str(e)}
    data = (obj or {}).get("data") or {}
    if obj.get("msg_type") != "Success":
        suffix, rc, rt = parse_result_code(data if isinstance(data, dict) else {})
        title, msg, act = lookup(suffix, ("EBA girişi başarısız",
                                          "Bilgiler alınamadı.",
                                          "Yeniden giriş yapın."))
        return False, {"title": title, "message": msg, "action": act,
                       "detail": f"{rc} {rt}".strip()}
    try:
        from credentials_manager import turkish_to_english
        uname = data["uname"]
        return True, {"name": uname,
                      "username": turkish_to_english(uname),
                      "tckn": data["tckn"],
                      "eba_id": data["uid"]}
    except KeyError as e:
        return False, {"title": "EBA cevabı eksik",
                       "message": "Gerekli alan gelmedi.",
                       "action": "Yeniden giriş yapın.",
                       "detail": f"eksik alan: {e}"}


def reset_password(token, password, tckn, timeout=TIMEOUT, session=None):
    """UsbPasswordChangerV7. (ok, hata|None)."""
    try:
        r = _http_post(url=EBA_PASSWORD_RESET_URL, headers=_headers(), timeout=timeout, session=session,
                       data={"authCode": token, "newPass": password,
                             "repPass": password, "user_tckn": tckn})
    except Exception as e:
        return False, {"title": NO_CONNECTION[0], "message": "Şifre EBA'ya kaydedilemedi.",
                       "action": NO_CONNECTION[2], "detail": str(e)}
    if r.status_code != 200:
        return False, {"title": "Parola EBA'ya kaydedilemedi",
                       "message": "EBA hatalı dönüş yaptı.",
                       "action": "Parolayı değiştirip tekrar deneyin; olmadıysa yeniden giriş yapın.",
                       "detail": f"HTTP {r.status_code}: {(r.text or '')[:300]}"}
    return True, None


def register_usb(tckn, password, eba_id, usb_serial, username, timeout=TIMEOUT, session=None):
    """RegisterUsbUser. (ok, sonuc). sonuc: hata dict'i ya da {'detail':...}."""
    try:
        r = _http_post(url=EBA_REGISTER_USB_URL, headers=_headers(), timeout=timeout, session=session,
                       json={"tckn": tckn, "password": password, "eba_id": eba_id,
                             "usb_serial": usb_serial, "username": username})
    except Exception as e:
        return False, {"title": NO_CONNECTION[0], "message": "Kayıt isteği gönderilemedi.",
                       "action": NO_CONNECTION[2], "detail": str(e)}
    if r.status_code != 200:
        return False, {"title": "USB oluşturulamaz",
                       "message": "EBA hatalı dönüş yaptı.",
                       "action": "Tekrar deneyin.",
                       "detail": f"HTTP {r.status_code}: {(r.text or '')[:300]}"}
    try:
        obj = r.json()
    except Exception as e:
        return False, {"title": "USB oluşturulamaz",
                       "message": "EBA cevabı okunamadı.",
                       "action": "Tekrar deneyin.",
                       "detail": str(e)}
    suffix, rc, rt = parse_result_code(obj or {})
    if suffix == "001":
        return True, {"detail": f"{rc} {rt}".strip()}
    title, msg, act = lookup(suffix, GENERIC_REGISTER)
    return False, {"title": title, "message": msg, "action": act,
                   "detail": f"{rc} {rt}".strip()}


def delete_usb(tckn, timeout=TIMEOUT, session=None):
    """DeleteUsbUser. (ok, sonuc). 006 = kayit yok (bilgi, hata degil)."""
    try:
        r = _http_post(url=EBA_DELETE_USB_URL, timeout=timeout, session=session,
                       params={"tckn": tckn})
    except Exception as e:
        return False, {"title": NO_CONNECTION[0], "message": "Silme isteği gönderilemedi.",
                       "action": NO_CONNECTION[2], "detail": str(e),
                       "not_found": False}
    if r.status_code != 200:
        return False, {"title": "Kayıt silinemedi",
                       "message": "EBA hatalı dönüş yaptı.",
                       "action": "Tekrar deneyin.",
                       "detail": f"HTTP {r.status_code}: {(r.text or '')[:300]}",
                       "not_found": False}
    try:
        obj = r.json()
    except Exception as e:
        return False, {"title": "Kayıt silinemedi",
                       "message": "EBA cevabı okunamadı.",
                       "action": "Tekrar deneyin.",
                       "detail": str(e), "not_found": False}
    suffix, rc, rt = parse_result_code(obj or {})
    if suffix == "001":
        return True, {"detail": f"{rc} {rt}".strip(), "not_found": False}
    if suffix == "006":
        return False, {"title": "Silinecek kayıt yok",
                       "message": "Bu TCKN'ye ait USB kaydı EBA'da yok.",
                       "action": "İşlem yapmanıza gerek yok.",
                       "detail": f"{rc} {rt}".strip(), "not_found": True}
    title, msg, act = lookup(suffix, GENERIC_DELETE)
    return False, {"title": title, "message": msg, "action": act,
                   "detail": f"{rc} {rt}".strip(), "not_found": False}
