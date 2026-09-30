"""Windows USB listeleme + pre-flight. Linux referans:
 - 1.0.10 list_removable_devices: removable==1 VE ro==0 (salt okunur listeye girmez)
 - 2.0.6: ro filtresi düşmüş (regresyon sayıldı) -> Windows'ta ro kontrolü ZORUNLU
 - USB SSD/HDD/NVMe kutulari Windows'ta FIXED (3) gorunur, REMOVABLE (2) degil.
   USB veri yolunda olduklari IOCTL_STORAGE_QUERY_PROPERTY (BusType==Usb) ile,
   o yetmezse WMI Win32_DiskDrive(InterfaceType='USB') eslemesiyle dogrulanip
   listeye alinir; dahili sabit diskler elenir.
 - Seri: ID_FS_UUID, FAT ör. "223C-F3F8" (kaynak yorum satırı). Windows
   GetVolumeInformation DWORD'u "XXXX-XXXX" büyük harf formatlanacak.
   Gerçek USB'de çift-OS karşılaştırması Windows testinde yapılacak.
"""

import os
import re

FAT_SERIAL_RE = re.compile(r"^[0-9A-F]{4}-[0-9A-F]{4}$")
ALLOWED_FS = {"FAT", "FAT32", "EXFAT", "FAT12"}


def format_win_serial(dword: int) -> str:
    dword &= 0xFFFFFFFF
    return f"{(dword >> 16) & 0xFFFF:04X}-{dword & 0xFFFF:04X}"


DRIVE_REMOVABLE = 2
DRIVE_FIXED = 3


def _drive_type(mountpoint):
    """Windows surucu tipi (2=Cikarilabilir, 3=Sabit, 5=CDROM...). Bilinmiyorsa None."""
    try:
        import win32file  # type: ignore
        return win32file.GetDriveType(mountpoint)
    except Exception:
        pass
    try:  # pywin32 yoksa stdlib ctypes ile ayni soru
        import ctypes
        t = ctypes.windll.kernel32.GetDriveTypeW(mountpoint)
        return int(t) if t else None
    except Exception:
        return None


def _is_usb_bus(mountpoint):
    """DRIVE_FIXED gorunen surucu USB veri yolunda mi? (USB SSD/HDD/NVMe kutusu).

    IOCTL_STORAGE_QUERY_PROPERTY ile STORAGE_DEVICE_DESCRIPTOR.BusType==Usb (7)
    aranir. Windows-disi ya da sorgu basarisizsa False."""
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
    except Exception:
        return False
    try:
        k32.CreateFileW.restype = ctypes.c_void_p
        k32.DeviceIoControl.restype = wintypes.BOOL
        vol = "\\\\.\\" + mountpoint[:2] if len(mountpoint) >= 2 and mountpoint[1] == ":" else mountpoint
        h = k32.CreateFileW(vol, 0, 1 | 2, None, 3, 0, None)
        if h in (0, -1, 0xFFFFFFFFFFFFFFFF):
            return False
        try:
            # STORAGE_PROPERTY_QUERY{PropertyId=0, QueryType=0} (12 bayt)
            query = (ctypes.c_byte * 12)()
            out = (ctypes.c_byte * 1024)()
            ret_len = wintypes.DWORD(0)
            ok = k32.DeviceIoControl(h, 0x2D1400, query, 12, out, 1024,
                                     ctypes.byref(ret_len), None)
            if not ok or ret_len.value < 32:
                return False
            bustype = int.from_bytes(bytes(out[28:32]), "little")
            return bustype == 7  # BusTypeUsb
        finally:
            k32.CloseHandle(h)
    except Exception:
        return False


def _mount_letter(mountpoint):
    mp = (mountpoint or "").upper()
    return mp[:2] if len(mp) >= 2 and mp[1] == ":" else mp


def _usb_drive_letters_wmi():
    """WMI Win32_DiskDrive(InterfaceType='USB') -> mantiksal surucu harfleri.

    Bazi USB-NVMe kopruleri BusType'i Nvme diye bildirir; IOCTL o zaman
    yakalayamaz, WMI denetleyici arayuzu uzerinden yakalar. Basarisizsa None."""
    try:
        import win32com.client  # type: ignore (pywin32)
        wmi = win32com.client.GetObject("winmgmts:")
        letters = set()
        for dd in wmi.ExecQuery(
                "SELECT DeviceID FROM Win32_DiskDrive WHERE InterfaceType='USB'"):
            try:
                did = str(dd.DeviceID).replace("'", "''")
                parts = wmi.ExecQuery(
                    "ASSOCIATORS OF {Win32_DiskDrive.DeviceID='%s'} "
                    "WHERE AssocClass=Win32_DiskDriveToDiskPartition" % did)
                for part in parts:
                    try:
                        pid = str(part.DeviceID).replace("'", "''")
                        lds = wmi.ExecQuery(
                            "ASSOCIATORS OF {Win32_DiskPartition.DeviceID='%s'} "
                            "WHERE AssocClass=Win32_LogicalDiskToPartition" % pid)
                        for ld in lds:
                            try:
                                letters.add(str(ld.DeviceID).upper())
                            except Exception:
                                pass
                    except Exception:
                        continue
            except Exception:
                continue
        return letters
    except Exception:
        return None


def list_usb_devices_win() -> list[dict]:
    """Removable + USB veri yolundaki mounted bölümler. Sabit harf YOK, kullanıcı seçer."""
    import psutil

    out: list[dict] = []
    usb_letters = None  # tembel: sadece FIXED gorunce WMI sorgulanir
    try:
        import win32api  # type: ignore
    except ImportError:
        win32api = None  # type: ignore

    for p in psutil.disk_partitions(all=False):
        try:
            dtype = _drive_type(p.mountpoint)
            if dtype == DRIVE_REMOVABLE:
                pass
            elif dtype == DRIVE_FIXED:
                if _is_usb_bus(p.mountpoint):
                    pass  # USB SSD/HDD/NVMe kutusu (BusType==Usb)
                else:
                    if usb_letters is None:
                        usb_letters = _usb_drive_letters_wmi() or set()
                    if _mount_letter(p.mountpoint) not in usb_letters:
                        continue
            else:
                continue

            fstype = (p.fstype or "").upper()
            # CDFS/UDF (ISO/Ventoy) -> listeye alma,_validator ayrıca hata verecek
            if fstype in ("CDFS", "UDF"):
                out.append({"device": p.device, "mountpoint": p.mountpoint,
                            "label": "", "fstype": fstype, "serial": "",
                            "blocked_reason": "ISO yazdırılmış medya desteklenmez"})
                continue

            label, serial_dw, fs = "", 0, fstype
            if win32api is not None:
                try:
                    label, serial_dw, _, _, fs = win32api.GetVolumeInformation(p.mountpoint)
                except Exception:
                    pass
            serial = format_win_serial(serial_dw) if serial_dw else ""
            out.append({"device": p.device, "mountpoint": p.mountpoint,
                        "label": label or p.device, "fstype": (fs or fstype).upper(),
                        "serial": serial, "blocked_reason": ""})
        except Exception:
            continue
    return out


def preflight(device: dict) -> tuple[bool, str, str]:
    """(ok, baslik, mesaj). ok=False -> 'oluşturulamaz' + sebep."""
    if not device:
        return False, "USB oluşturulamaz", "USB seçilmedi."
    if device.get("blocked_reason"):
        return False, "USB oluşturulamaz", device["blocked_reason"] + " Standart bir USB bellek kullanın."
    mp = device.get("mountpoint") or ""
    if not mp or not os.path.isdir(mp):
        return False, "USB oluşturulamaz", "USB bağlı değil veya formatlanmamış. Diski bağlayın ya da FAT32 formatlayın."
    serial = device.get("serial") or ""
    if not serial or serial == "0000-0000":
        return False, "USB oluşturulamaz", "USB seri numarası okunamadı. Başka port/bilgisayar deneyin."
    if not FAT_SERIAL_RE.match(serial):
        return False, "USB oluşturulamaz", f"Seri formatı desteklenmiyor ({serial}). FAT32/exFAT formatlayın."
    if (device.get("fstype") or "").upper() not in ALLOWED_FS:
        return False, "USB oluşturulamaz", f"Dosya sistemi desteklenmiyor ({device.get('fstype')}). FAT32/exFAT kullanın."
    # yazılabilirlik (1.0.10 ro==0 karşılığı)
    try:
        probe = os.path.join(mp, ".eta_write_test")
        with open(probe, "wb") as f:
            f.write(b"1")
        os.remove(probe)
    except Exception:
        return False, "USB oluşturulamaz", "USB salt okunur. Kilit anahtarını açın veya FAT32 formatlayın."
    return True, "", ""
