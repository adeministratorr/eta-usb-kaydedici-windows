"""Flash dogrulama: bu USB tahtada calisacak mi? Kime ait?

Tahtanin yaptigi kontrollerin Windows karsiligi (eta-usb-login/service.py:78-148):
 1) .credentials var ve cozumlenebiliyor mu (SafeUnpickler + hex + json)
 2) dosyadaki usb_serial == takili USB'nin gercek serisi mi
 3) (internet sart, ulasilamazsa dogrulama gecemez) EBA GetUsbUser EBA.001 donuyor mu
Parola hash'i gosterilmez, sadece var/yok + bcrypt formati gecerli mi.
"""

import binascii
import io
import json
import os
import pickle

CREDENTIALS_NAME = ".credentials"


class SafeUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "builtins" and name in {"dict", "list", "str", "int", "float", "bool", "tuple"}:
            return getattr(__builtins__, name)
        raise pickle.UnpicklingError("global '%s.%s' is forbidden" % (module, name))


# Gercek .credentials ~1KB'dir. Buyuk dosya = bozuk ya da tuzak (bellek sismesine karsi).
MAX_CREDENTIALS_SIZE = 256 * 1024


def read_credentials_file(path):
    """(dict|None, hata_mesaji|None). Tahta credentials.py ile ayni mantik."""
    try:
        if os.path.getsize(path) > MAX_CREDENTIALS_SIZE:
            return None, "Dosya anormal derecede büyük, açılmadı. Yeniden kaydedin."
        with open(path, "rb") as f:
            ctx = f.read(MAX_CREDENTIALS_SIZE + 1)
    except FileNotFoundError:
        return None, "Bu USB'de .credentials dosyası yok. Henüz kaydedilmemiş olabilir."
    except Exception as e:
        return None, f"Dosya okunamadı: {e}"
    try:
        loaded = SafeUnpickler(io.BytesIO(ctx)).load()
        loaded = binascii.unhexlify(loaded)
        data = json.loads(loaded.decode("utf-8"))
    except Exception:
        return None, "Dosya bozuk veya bu uygulamayla oluşturulmamış."
    if not isinstance(data, dict):
        return None, "Dosya bozuk veya bu uygulamayla oluşturulmamış."
    return data, None


def check_eba_record(eba_id, usb_serial, timeout=15, session=None):
    """Tahtanin giris oncesi yaptigi kontrol (user.py:42-57). (ok, mesaj)."""
    import requests

    url = "https://giris.eba.gov.tr/EBA_GIRIS/GetUsbUser"
    try:
        if session is not None:
            r = session.post(url, json={"eba_id": eba_id, "usb_serial": usb_serial}, timeout=timeout)
        else:
            r = requests.post(url, json={"eba_id": eba_id, "usb_serial": usb_serial}, timeout=timeout)
    except Exception:
        return None, "EBA'ya ulaşılamadı, sunucu kontrolü atlandı."
    try:
        txt = r.text or ""
    except Exception:
        return None, "EBA cevabı okunamadı."
    if "EBA.001" in txt:
        return True, "EBA kaydı doğrulandı."
    if "EBA.101" in txt:
        return False, "EBA'da kayıt bulunamadı (EBA.101). USB'yi yeniden kaydedin."
    return False, "EBA doğrulaması başarısız."


def verify_flash(device, check_server=True, session=None):
    """device: usb_manager_win.list_usb_devices_win() öğesi.
    Döner: {"ok": bool, "owner": {...}, "checks": [(ad, ok, mesaj)]}.
    owner: name, username, usb_serial (dosyadaki), eba_id (maskeli)."""
    checks = []
    mp = (device or {}).get("mountpoint") or ""
    if not mp or not os.path.isdir(mp):
        return {"ok": False, "owner": None,
                "checks": [("USB bağlı", False, "USB bağlı değil.")]}

    data, err = read_credentials_file(os.path.join(mp, CREDENTIALS_NAME))
    if err:
        hint = ""
        try:
            from virus_cleaner import find_credentials_files
            moved_all = find_credentials_files(mp)
            # Kökteki dosyanın kendisi "taşınmış" sayılmaz; sadece alt
            # klasördekiler ipucu vermeli. Yoksa bozuk kök dosya varken
            # bile "taşınmış görünüyor" deniyordu.
            moved = [p for p in moved_all
                     if os.path.normpath(p).lower() != CREDENTIALS_NAME.lower()]
            if moved:
                hint = (f" Dosya başka klasöre taşınmış görünüyor ({moved[0]})."
                        " USB Virüs Temizle ile köke iade edin.")
        except Exception:
            pass
        return {"ok": False, "owner": None, "checks": [("Dosya", False, err + hint)]}
    checks.append(("Dosya okundu", True, "Kayıt dosyası sağlam."))

    for key in ("eba_id", "username", "usb_serial", "password"):
        if key not in data:
            return {"ok": False, "owner": None,
                    "checks": checks + [("İçerik", False, f"Dosyada '{key}' alanı yok. Yeniden kaydedin.")]}

    real_serial = (device or {}).get("serial") or ""
    if real_serial and data["usb_serial"] != real_serial:
        checks.append(("Seri eşleşmesi", False,
                       f"Dosyadaki seri ({data['usb_serial']}) bu USB'nin serisiyle ({real_serial}) uyuşmuyor. Başka USB'ye kopyalanmış olabilir."))
        serial_ok = False
    else:
        checks.append(("Seri eşleşmesi", True, "Dosya bu USB'ye ait."))
        serial_ok = True

    pw = str(data.get("password") or "")
    if pw.startswith("$2") and len(pw) >= 50:
        checks.append(("Parola kaydı", True, "Parola hash'i geçerli formatta."))
    else:
        checks.append(("Parola kaydı", False, "Parola kaydı bozuk. Yeniden kaydedin."))
        return {"ok": False, "owner": _owner(data), "checks": checks}

    if check_server:
        ok, msg = check_eba_record(data["eba_id"], data["usb_serial"], session=session)
        if ok is True:
            checks.append(("EBA kaydı", True, msg))
        elif ok is False:
            checks.append(("EBA kaydı", False, msg))
        else:
            checks.append(("EBA kaydı", "skipped",
                           f"İnternet olmadığından EBA kontrolü atlandı ({msg})"))

    ok = all(c[1] is True or c[1] == "skipped" for c in checks)
    return {"ok": ok and serial_ok, "owner": _owner(data), "checks": checks}


def _owner(data):
    eba_id = str(data.get("eba_id") or "")
    masked = (eba_id[:3] + "***" + eba_id[-3:]) if len(eba_id) > 6 else "***"
    return {"name": data.get("name") or data.get("username") or "?",
            "username": data.get("username") or "?",
            "usb_serial": data.get("usb_serial") or "?",
            "eba_id_masked": masked}
