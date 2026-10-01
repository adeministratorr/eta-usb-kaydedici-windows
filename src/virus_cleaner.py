"""Musallat / kisayol (.lnk) virusu temizligi: flash + (Windows) PC.

Kanonik recete (klasik temizleme rehberleri): kokteki TUM .lnk'lar silinir,
`attrib -h -r -s /s /d` ile her sey ozyinelemeli geri acilir,
autorun.inf + supheli dosyalar temizlenir. Birebir aynisi burada.

Klasik bulasma: kokteki klasorler gizlenip yerlerine ayni isimde .lnk
birakilir; ayrica autorun.inf + Musallat.exe / Ozel Dosyalar.exe gibi
zararlilar; icerik tek bir zulalama klasorune tasinmis olabilir:
isimsiz klasor (Alt+0160 NBSP) veya surucu etiketiyle ayni isimli
klasor (örn. KINGSTON). Temizlik bitince zulalama icerigi kok'e
tasinir. .credentials baska klasore tasinmis/silinmis olabilir.

Tahta okumaya mudahale yok: tahta dosyayi isimle acar (ro mount);
biz kokteki .lnk/autorun/supheli dosyalari silip gizlenenleri
ozyinelemeli geri aciyoruz ve .credentials'i koke iade ediyoruz.

Guvenlik: kokteki .lnk'larin tamami + bilinen zararli isimler +
calistirilabilir supheli uzantilar (.scr/.pif/.com/.bat/.vbs/.js + .ini/.bak/.bin) silinir.
Kokteki desktop.ini'ye virus yazar, kesin silinir (virüs artığı).
Musallat yayilimi olan klasor taklidi .exe'ler (DH/ + yaninda DH.exe gibi,
kok + alt klasorler) onayli silinir; buyuk (>1MB) eslesmeler mesru
olabileceginden suspicious'ta listelenir.
usbshow portu: alt klasorlerdeki .lnk/.inf artıkları + Temp'te *.com ve
isimde gecen masquerade (*wuauclt* vb.) de onayli silinir.
Diger bilinmeyen .exe'lere dokunulmaz, onay ekraninda listelenir.
"""

import os
import shutil

CREDENTIALS_NAME = ".credentials"

# Koke iade / silmede dokunulmayacak sistem klasorleri
SKIP_DIRS = {"system volume information", "$recycle.bin", ".trash", ".trashes"}

# Otomatik silinecek bilinen zararlilar (kucuk harf karsilastirilir)
KNOWN_BAD = {
    "autorun.inf",
    "musallat.exe",
    "ozel dosyalar.exe",
    "özel dosyalar.exe",
    "ravmon.exe",
    "autorun.vbs",
    "wsscript.exe",
}

# Gozlem: virus Temp'te sistem sureci taklidi yapar
# (wuauclt, rundll32, TrustedInstaller, msiexec...). Gercek konumlari
# disinda gorunurlerse zararli sayilir.
MASQUERADE_NAMES = {
    "wuauclt.exe", "rundll32.exe", "trustedinstaller.exe", "msiexec.exe",
    "svchost.exe", "csrss.exe", "winlogon.exe", "services.exe",
    "lsass.exe", "dwm.exe", "smss.exe", "spoolsv.exe",
}


def _system_dirs():
    root = os.environ.get("SystemRoot", r"C:\Windows").rstrip("\\/")
    return (root.lower() + "\\system32", root.lower() + "\\syswow64")


def _is_real_system_process(exe_path):
    """Sistem taklidi mi? Gercek System32/SysWOW64 disindaysa sahte."""
    if not exe_path:
        return False
    p = exe_path.replace("/", "\\").lower()
    return p.startswith(_system_dirs())

# macOS Finder FAT/exFAT USB'ye AppleDouble izleri bırakır (._*, .DS_Store)
# + Windows thumbs.db. Bunlar virüs değil, tahtayı etkilemez; taramada yok sayılır.
# NOT: kokteki desktop.ini bilerek IGNORED degil -> .ini kuraliyla onayli silinir.
IGNORED_NAMES = {".ds_store", "thumbs.db"}


def _is_os_junk(name):
    ln = (name or "").lower()
    return ln.startswith("._") or ln in IGNORED_NAMES


# Otomatik silinecek supheli uzantilar (kokte; tasinabilir .exe HARIC:
# tasinabilir uygulamalar korunur, onay ekraninda listelenir)
DELETE_EXTS = {".scr", ".pif", ".com", ".bat", ".vbs", ".js"}

# Silinmez, onay ekraninda "elle bakin" diye listelenir
REPORT_SUFFIX = ".exe"

# Klasor taklidi .exe'ler icin guvenlik siniri: Musallat klonlari ~130KB
# (132608 byte). Mesru tasinabilir uygulamalar genelde cok daha buyuktur;
# yanlis pozitifleri onlemek icin buyuk (>1MB) klonlar otomatik silinmez,
# suspicious listesinde gosterilir.
CLONE_EXE_SIZE_LIMIT = 1 * 1024 * 1024


# ---------- Windows dosya oznitelikleri (diger OS'te no-op) ----------

def _on_win():
    return os.name == "nt"


def is_admin():
    """Yonetici mi? Windows disi her zaman False."""
    if not _on_win():
        return False
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_admin():
    """Yonetici degilse UAC ile kendini yukseltip eski sureci kapatir.
    Yoneticiyse / Windows-disiysa False doner, hicbir sey yapmaz."""
    if is_admin() or not _on_win():
        return False
    import ctypes
    import sys
    if getattr(sys, "frozen", False):
        exe, params = sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
    else:
        exe = sys.executable
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{script}"'] + [f'"{a}"' for a in sys.argv[1:]])
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    if rc and int(rc) > 32:
        os._exit(0)
    return False


def _get_attrs(path):
    import ctypes
    INVALID = 0xFFFFFFFF
    v = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    return None if v == INVALID else v


def clear_attrs(path):
    """Gizli/sistem/salt-okunur bayraklarini kaldir (silmeden once)."""
    if not _on_win():
        return False
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x80))
    except Exception:
        return False


def protect_credentials(path):
    """Kokteki .credentials'e Gizli+Sistem ver. Tahta Linux oldugu icin
    FAT ozniteliklerini yok sayar, okumaya engel degildir."""
    if not _on_win():
        return False
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.SetFileAttributesW(str(path), 0x02 | 0x04))
    except Exception:
        return False


def is_hidden(path):
    if not _on_win():
        return False
    try:
        v = _get_attrs(path)
        return v is not None and bool(v & (0x02 | 0x04))
    except Exception:
        return False


def _safe_remove(path):
    """Yalnizca DOSYA siler. Klasorse dokunmaz (rmtree yok):
    virus adli klasorun icinde kullanici dosyasi olabilir."""
    clear_attrs(path)
    if os.path.isdir(path) and not os.path.islink(path):
        raise IsADirectoryError(f"Klasör silinmedi (elle inceleyin): {path}")
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# ---------- Flash tarama / temizleme ----------

def _entries(root):
    try:
        return os.listdir(root)
    except Exception:
        return []


def find_credentials_files(root):
    """Surucudeki tum .credentials dosyalarinin kok'e goreli yollari."""
    found = []
    for dirpath, dirnames, filenames in os.walk(root):
        # sistem klasorlerine + macOS izlerine girme
        dirnames[:] = [d for d in dirnames
                       if d.lower() not in SKIP_DIRS
                       and d.lower() != "__macosx"
                       and not _is_os_junk(d)]
        for fn in filenames:
            if _is_os_junk(fn):
                continue
            if fn.lower() == CREDENTIALS_NAME:
                full = os.path.join(dirpath, fn)
                found.append(os.path.relpath(full, root))
    return found


def _is_stash_name(name):
    """Virusun icerik sakladigi isimsiz/anlamsiz klasor adi mi?
    Bosluk/nokta ya da hic harf-rakam icermeyen isimler.
    Alt+0160 / Alt+255 ile uretilen NBSP (\\xa0), sifir-genislik
    (\\u200b) gibi gorunmez karakterler de buraya girer."""
    s = (name or "").replace("\xa0", "").replace("\u200b", "").strip()
    if s in ("", ".", ".."):
        return True
    return not any(ch.isalnum() for ch in s)


def get_volume_label(root):
    """USB surucunun Volume Label'ini dondur (Windows).
    Basarisizsa / Windows-disinda bos string."""
    try:
        if not _on_win():
            return ""
        mp = str(root or "")
        if len(mp) >= 2 and mp[1] == ":" and not mp.endswith(("\\", "/")):
            mp += "\\"
        try:
            import win32api  # type: ignore
            label, _, _, _, _ = win32api.GetVolumeInformation(mp)
            return (label or "").strip()
        except Exception:
            pass
        try:
            import ctypes
            from ctypes import wintypes
            vol = wintypes.create_unicode_buffer(256)
            fs = wintypes.create_unicode_buffer(256)
            serial = wintypes.DWORD(0)
            maxlen = flags = wintypes.DWORD(0)
            ok = ctypes.windll.kernel32.GetVolumeInformationW(
                mp, vol, 256, ctypes.byref(serial),
                ctypes.byref(maxlen), ctypes.byref(flags), fs, 256)
            if ok:
                return (vol.value or "").strip()
        except Exception:
            pass
    except Exception:
        pass
    return ""


def _is_label_stash(name, label):
    """Klasor adi surucu etiketiyle ayni mi?
    Virus varyantlarindan biri USB'nin Volume Label'i ile ayni isimde
    klon klasor uretir (örn. KINGSTON). Device yolu (/dev/..., E:)
    gbi gecersiz etiketler elenir."""
    if not name or not label:
        return False
    lab = (label or "").strip()
    if not lab or "/" in lab or "\\" in lab or ":" in lab:
        return False
    return (name or "").strip().lower() == lab.lower()


def _unique_dest(root, name):
    dest = os.path.join(root, name)
    if not os.path.exists(dest):
        return dest
    stem, ext = os.path.splitext(name)
    i = 1
    while True:
        cand = os.path.join(root, f"{stem} (kurtarılan{'' if i == 1 else f' {i}'}){ext}")
        if not os.path.exists(cand):
            return cand
        i += 1


def _norm_clone(name):
    """Klasor/.exe ikiz karsilastirmasi icin normalize et."""
    try:
        return (name or "").strip().casefold()
    except Exception:
        return (name or "").strip().lower()


def _find_folder_clones(root):
    """Musallat yayilimi: gizlenen klasorun yanina ayni isimli .exe.

    Ornek: `DH/` klasoru + yaninda `DH.exe` (yaklasik 130KB). Koke + tum alt
    klasorlere ozyinelemeli bakilir; ayni ebeveyndeki eslesmeler doner.
    Donus: [{"rel": koke-goreli-yol, "size": byte, "hidden_twin": bool}].
    Boyut filtresi uygulanmaz; buyuk/kucuk ayrimi scan_flash'ta yapilir."""

    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Sistem / cop klasorlerine girme, taramada yok sayilanlari ele
        dirnames[:] = [d for d in dirnames
                       if d.lower() not in SKIP_DIRS
                       and d.lower() != "__macosx"
                       and not _is_os_junk(d)]
        # Ayni ebeveyndeki klasor adlari (normalize -> gercek ad)
        dir_map = {}
        for d in dirnames:
            if _is_os_junk(d):
                continue
            # Zulalama (isimsiz/etiket) klasorun kendisi ikiz sayilmaz
            if _is_stash_name(d):
                continue
            dir_map.setdefault(_norm_clone(d), d)
        if not dir_map:
            continue
        for fn in filenames:
            if _is_os_junk(fn):
                continue
            if not fn.lower().endswith(REPORT_SUFFIX):
                continue
            if fn.lower() in KNOWN_BAD:
                continue
            stem = os.path.splitext(fn)[0]
            twin = dir_map.get(_norm_clone(stem))
            if not twin:
                continue
            full = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full) if os.path.isfile(full) else 0
            except Exception:
                size = 0
            try:
                hidden_twin = is_hidden(os.path.join(dirpath, twin))
            except Exception:
                hidden_twin = False
            try:
                rel = os.path.relpath(full, root)
            except Exception:
                rel = fn
            out.append({"rel": rel, "size": size, "hidden_twin": hidden_twin})
    out.sort(key=lambda x: x["rel"].lower())
    return out


def _find_sub_virus_files(root):
    """usbshow Form2 altdosya portu (guvenli alt kume): alt klasorlerdeki
    .lnk + .inf artıkları. Koktekiler zaten ayri listelerde; burada sadece
    kok disi (dirpath != root) taranir. .ini/.bak/.bin alt klasorlerde
    mesru olabilir, dokunulmaz."""
    lnks, infs = [], []
    try:
        root_norm = os.path.normcase(os.path.abspath(root))
    except Exception:
        root_norm = root
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames
                       if d.lower() not in SKIP_DIRS
                       and d.lower() != "__macosx"
                       and not _is_os_junk(d)]
        try:
            is_root = os.path.normcase(os.path.abspath(dirpath)) == root_norm
        except Exception:
            is_root = (dirpath == root)
        if is_root:
            continue
        for fn in filenames:
            if _is_os_junk(fn):
                continue
            ln = fn.lower()
            full = os.path.join(dirpath, fn)
            try:
                rel = os.path.relpath(full, root)
            except Exception:
                continue
            if ln.endswith(".lnk"):
                lnks.append(rel)
            elif ln.endswith(".inf"):
                infs.append(rel)
    lnks.sort(key=str.lower)
    infs.sort(key=str.lower)
    return lnks, infs


def scan_flash(root, volume_label=None):
    """Silmeden tarar. Bulgular sozlugu doner.
    volume_label verilirse (UI'daki cihaz listesinden) o kullanilir,
    verilmezse get_volume_label() ile surucuden okunmaya calisilir."""
    res = {"root": root, "autorun": False, "bad_exes": [],
           "shortcut_hits": [], "orphan_lnks": [], "hidden": [],
           "stash": [], "suspicious": [], "credentials": [], "error": "",
           "label": "", "folder_clones": [], "sub_lnks": [], "sub_infs": []}
    if not root or not os.path.isdir(root):
        res["error"] = "USB bağlı değil."
        return res
    label = (volume_label or "").strip() or get_volume_label(root)
    res["label"] = label
    items = _entries(root)
    lower = {e.lower(): e for e in items}
    paths = {e: os.path.join(root, e) for e in items}

    if "autorun.inf" in lower and os.path.isfile(paths[lower["autorun.inf"]]):
        res["autorun"] = True

    dirs = {e for e in items
            if os.path.isdir(paths[e]) and e.lower() not in SKIP_DIRS}

    for e in items:
        p = paths[e]
        if not os.path.isfile(p):
            continue
        if _is_os_junk(e):
            continue
        ln = e.lower()
        ext = os.path.splitext(ln)[1]
        if ln in KNOWN_BAD and ln != "autorun.inf":
            res["bad_exes"].append(e)
        elif ln.endswith(".lnk"):
            stem = ln[:-4]
            match = next((d for d in dirs if d.lower() == stem), None)
            if match:
                res["shortcut_hits"].append({"lnk": e, "folder": match})
            else:
                res["orphan_lnks"].append(e)
        elif ext in DELETE_EXTS:
            res["bad_exes"].append(f"{e} (şüpheli uzantı)")
        elif ln == "desktop.ini":
            # Kokteki desktop.ini'ye virus yazar (usbshow da siler).
            # Kesin silinecek: onayli silme listesinde.
            res["bad_exes"].append(f"{e} (virüs artığı)")
        elif ext in (".ini", ".bak", ".bin"):
            # .ini/.bak/.bin kokte supheli sayilir, onayli silinir.
            # thumbs.db / .DS_Store _is_os_junk'ta eleniyor, korunur.
            res["bad_exes"].append(f"{e} (şüpheli uzantı)")
        elif ext == REPORT_SUFFIX:
            res["suspicious"].append(e)

    # Musallat yayilimi: klasor adiyla ayni isimli .exe (kok + alt klasorler).
    # Ornek: DH/ + yaninda DH.exe. Ayni ebeveyndeki eslesme guclu virus
    # isaretidir. Kucuk (<=1MB) olanlar onayli silinir; buyuk (>1MB)
    # olanlar mesru olabileceginden suspicious'ta listelenir.
    try:
        clones = _find_folder_clones(root)
    except Exception:
        clones = []
    small = [c for c in clones if (c.get("size") or 0) <= CLONE_EXE_SIZE_LIMIT]
    large = [c for c in clones if (c.get("size") or 0) > CLONE_EXE_SIZE_LIMIT]
    res["folder_clones"] = [c["rel"] for c in small]
    if small:
        clone_roots = {os.path.basename(c["rel"]) for c in small}
        # Kokteki kucuk klonlar yukarida suspicious'a dusmustu, oradan cikar
        res["suspicious"] = [s for s in res["suspicious"] if s not in clone_roots]
    for c in large:
        rel = c["rel"]
        # Kokteki buyuk klon zaten suspicious'ta (basename); alt klasordeki
        # buyuk klon suspicious'a goreceli yolla eklenir.
        if os.path.dirname(rel):
            if rel not in res["suspicious"]:
                res["suspicious"].append(rel)
        elif os.path.basename(rel) not in res["suspicious"]:
            res["suspicious"].append(os.path.basename(rel))

    res["hidden"] = [e for e in items if is_hidden(paths[e])]
    # Zulalama klasorleri: iki varyant
    #  1) isimsiz / anlamsiz adli (Alt+0160 NBSP vb.) -> her zaman supheli
    #  2) surucu etiketiyle ayni adli (örn. KINGSTON) -> virus bulgusu
    #     varsa supheli (es isimli .lnk ikizi, autorun, bilinen zararli,
    #     sahipsiz .lnk veya gizli oge). Bulgusuz tek basina ayni isimli
    #     klasor kullanicinin gercek klasoru olabilir, ellemeyiz.
    lnk_stems = {e.lower()[:-4] for e in items
                 if e.lower().endswith(".lnk")
                 and os.path.isfile(paths[e])}
    virus_signals = bool(res["autorun"] or res["bad_exes"]
                         or res["shortcut_hits"] or res["orphan_lnks"]
                         or res["hidden"] or res["folder_clones"])
    # usbshow Form2 altdosya portu: alt klasorlerdeki .lnk/.inf artıkları
    try:
        sub_lnks, sub_infs = _find_sub_virus_files(root)
    except Exception:
        sub_lnks, sub_infs = [], []
    res["sub_lnks"] = sub_lnks
    res["sub_infs"] = sub_infs
    virus_signals = bool(virus_signals or sub_lnks or sub_infs)
    for d in sorted(dirs):
        if _is_os_junk(d):
            continue
        blank = _is_stash_name(d)
        label_hit = _is_label_stash(d, label)
        if not (blank or label_hit):
            continue
        if label_hit and not blank:
            twin_lnk = d.lower() in lnk_stems
            if not (twin_lnk or virus_signals):
                continue
            why = "etiket"
        else:
            why = "isimsiz"
        try:
            inside = os.listdir(os.path.join(root, d))
        except Exception:
            inside = []
        res["stash"].append({"folder": d, "items": inside, "why": why})
    res["credentials"] = find_credentials_files(root)
    return res


def clean_flash(root, volume_label=None):
    """Tarar, bilinen zararlilari temizler, gizlileri acar,
    kokteki desktop.ini + klasor taklidi .exe'leri (kok + alt klasorler) +
    alt klasor .lnk/.inf artıklarını siler,
    zulalama klasorune (isimsiz veya surucu etiketli) tasinan icerigi
    koke iade eder, .credentials'i koke iade eder. Rapor doner."""
    rep = {"removed": [], "unhidden": [], "restored_items": [],
           "restored": "", "kept": [], "errors": []}
    scan = scan_flash(root, volume_label=volume_label)
    if scan["error"]:
        rep["errors"].append(scan["error"])
        return rep

    if scan["autorun"]:
        try:
            _safe_remove(os.path.join(root, "autorun.inf"))
            rep["removed"].append("autorun.inf")
        except Exception as e:
            rep["errors"].append(f"autorun.inf silinemedi: {e}")

    for name in scan["bad_exes"]:
        real = name.split(" (")[0]
        try:
            _safe_remove(os.path.join(root, real))
            rep["removed"].append(name)
        except Exception as e:
            rep["errors"].append(f"{name} silinemedi: {e}")

    # Musallat klonlari: klasor adiyla ayni isimli .exe (kok + alt klasorler).
    # Ornek: DH/ + DH.exe. Ayni ebeveyndeki eslesme silinir.
    for rel in scan.get("folder_clones", []):
        try:
            _safe_remove(os.path.join(root, rel))
            rep["removed"].append(f"{rel} (klasör taklidi)")
        except Exception as e:
            rep["errors"].append(f"{rel} silinemedi: {e}")

    # Kokteki TUM .lnk'lar (kanonik recete: del *.lnk)
    matched = {h["lnk"] for h in scan["shortcut_hits"]}
    for lnk in [h["lnk"] for h in scan["shortcut_hits"]] + scan["orphan_lnks"]:
        try:
            _safe_remove(os.path.join(root, lnk))
            tag = "(kısayol virüsü)" if lnk in matched else "(sahipsiz kısayol)"
            rep["removed"].append(f"{lnk} {tag}")
        except Exception as e:
            rep["errors"].append(f"{lnk} silinemedi: {e}")

    # usbshow Form2 altdosya portu: alt klasorlerdeki .lnk/.inf artıkları
    for rel in scan.get("sub_lnks", []):
        try:
            _safe_remove(os.path.join(root, rel))
            rep["removed"].append(f"{rel} (alt klasör kısayolu)")
        except Exception as e:
            rep["errors"].append(f"{rel} silinemedi: {e}")
    for rel in scan.get("sub_infs", []):
        try:
            _safe_remove(os.path.join(root, rel))
            rep["removed"].append(f"{rel} (alt klasör inf)")
        except Exception as e:
            rep["errors"].append(f"{rel} silinemedi: {e}")

    # Ozyinelemeli geri acma (kanonik: attrib -h -r -s /s /d)
    unhidden_count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d.lower() not in SKIP_DIRS]
        for entry in [dirpath] + [os.path.join(dirpath, x) for x in dirnames + filenames]:
            try:
                if clear_attrs(entry):
                    unhidden_count += 1
                    if os.path.dirname(entry) == root:
                        rep["unhidden"].append(os.path.basename(entry))
            except Exception:
                pass
    if unhidden_count and not rep["unhidden"]:
        rep["unhidden"].append(f"+ alt klasörlerde {unhidden_count} öğe")

    # Zulalama klasorune tasinan icerigi eski konumuna (koke) iade et.
    # Iki varyant: isimsiz (Alt+0160 NBSP) veya surucu etiketiyle ayni
    # isimli klasor (örn. KINGSTON). Tarama anindaki liste yerine guncel
    # icerik okunur; boylece .lnk silme / attrib acma sonrasi durum gecerlidir.
    for stash in scan["stash"]:
        folder = os.path.join(root, stash["folder"])
        try:
            live_items = os.listdir(folder)
        except Exception as e:
            rep["errors"].append(f"{stash['folder']} okunamadı: {e}")
            continue
        for item in live_items:
            if _is_os_junk(item) or item.lower() == "desktop.ini":
                continue
            src = os.path.join(folder, item)
            # Klasor dasinabilir, dosya/dizin fark etmez; toptan koke tasinir.
            # _safe_remove degil: klasor icerigi korunmalidir.
            try:
                clear_attrs(src)
                dest = _unique_dest(root, item)
                shutil.move(src, dest)
                shown = os.path.basename(dest)
                rep["restored_items"].append(
                    f"{stash['folder']}/{item} → {shown}" if shown != item
                    else f"{stash['folder']}/{item} → kök")
            except Exception as e:
                rep["errors"].append(f"{stash['folder']}/{item} iade edilemedi: {e}")
        try:
            if not os.listdir(folder):
                os.rmdir(folder)
                rep["removed"].append(f"{stash['folder']} (boş zulalama klasörü)")
        except Exception:
            pass

    root_cred = os.path.join(root, CREDENTIALS_NAME)
    if not os.path.exists(root_cred):
        others = [c for c in find_credentials_files(root)
                  if os.path.basename(c) == CREDENTIALS_NAME]
        if others:
            try:
                shutil.move(os.path.join(root, others[0]), root_cred)
                rep["restored"] = f".credentials köke iade edildi ({others[0]})"
            except Exception as e:
                rep["errors"].append(f".credentials iade edilemedi: {e}")

    if os.path.exists(root_cred):
        protect_credentials(root_cred)

    rep["kept"] = scan["suspicious"]
    return rep


# ---------- PC temizligi (yalnizca Windows) ----------

# Arastirma sonucu ureten dosyalarin saklandigi yerler:
# - %TEMP%\<rastgele>.vbs + tmpXXXX.tmp.exe (kisayol virusu cekirdegi)
# - Startup\<rastgele>.vbs (dogrudan vbs, lnk degil!)
# - HKCU Run: rastgele adli degerler (WXCKYz, ZGFYszaas...), wscript //B
# - HKCU Run: MusaLLat.exe (birden cok TR kaynagi dogruladi)
# Sira: surec oldur -> Temp/Startup dosyalari sil -> Run kayitlari sil.

TEMP_VBS_SWEEP = True  # %TEMP% icindeki *.vbs'ler onay ekraninda listelenir


def _sweep_dir(path):
    """Klasordeki KNOWN_BAD + *.vbs/*.com + sistem-taklidi dosyalari.
    OS bagimsiz, test edilebilir. usbshow Form4 portu: Temp'te isim
    icinde gecen masquerade adlari (*wuauclt* vb.) + *.com da suphelidir;
    gercek sistem dosyalari Temp'te yasamaz."""
    # Masquerade taban adlari (uzantisiz): Temp'te substring eslesir
    _MASQ_BASE = {n.lower().removesuffix(".exe") for n in MASQUERADE_NAMES}
    _MASQ_BASE |= {"lmkamcx"}
    out = []
    try:
        for e in os.listdir(path):
            full = os.path.join(path, e)
            if not os.path.isfile(full):
                continue
            ln = e.lower()
            if (ln in KNOWN_BAD or ln in MASQUERADE_NAMES
                    or (TEMP_VBS_SWEEP and ln.endswith(".vbs"))
                    or ln.endswith(".com")
                    or any(b in ln for b in _MASQ_BASE)):
                out.append(full)
    except Exception:
        pass
    return out


def _wscript_is_malicious(cmdline):
    """wscript/cscript ornegi supheli mi? Komut satirinda Temp/Startup
    veya .vbs isareti varsa evet."""
    args = " ".join(cmdline or []).lower()
    return ("\\temp\\" in args or "\\tmp\\" in args or "startup" in args
            or ".vbs" in args or ".js" in args)


def _shortcut_target(path):
    try:
        from win32com.client import Dispatch
        sh = Dispatch("WScript.Shell")
        return (sh.CreateShortcut(str(path)).TargetPath or "").strip()
    except Exception:
        return ""


def scan_pc():
    """Baslangic klasoru + HKCU Run + Gorev Yoneticisi kilidi + calisan
    zararli surecler. Silmez, sadece bulur. (MEB rehberi: Musallat
    Gorev Yoneticisi'ni engeller -> Policies\\System anahtari.)"""
    if not _on_win():
        return {"supported": False, "startup": [], "run": [],
                "policies": [], "processes": [], "temp": [], "startup_files": [],
                "run_machine": [], "startup_machine": [],
                "note": "PC temizliği yalnızca Windows'ta çalışır."}
    import win32file

    findings = {"supported": True, "startup": [], "run": [],
                "policies": [], "processes": [], "temp": [], "startup_files": [],
                "run_machine": [], "startup_machine": [],
                "note": ""}
    startup = os.path.join(os.environ.get("APPDATA", ""),
                           r"Microsoft\Windows\Start Menu\Programs\Startup")
    findings["startup_files"] = _sweep_dir(startup)
    try:
        tempdir = os.environ.get("TEMP") or os.environ.get("TMP") or ""
        if tempdir:
            findings["temp"] = _sweep_dir(tempdir)
    except Exception:
        pass
    try:
        for e in os.listdir(startup):
            if not e.lower().endswith(".lnk"):
                continue
            p = os.path.join(startup, e)
            tgt = _shortcut_target(p)
            base = os.path.basename(tgt).lower()
            removable = False
            if len(tgt) > 1 and tgt[1] == ":":
                try:
                    removable = win32file.GetDriveType(tgt[:3]) == 2
                except Exception:
                    removable = False
            if removable or base in KNOWN_BAD:
                findings["startup"].append({"lnk": p, "target": tgt})
    except FileNotFoundError:
        pass
    except Exception as e:
        findings["note"] = f"Başlangıç klasörü okunamadı: {e}"

    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run")
        i = 0
        while True:
            try:
                name, val, _ = winreg.EnumValue(key, i)
            except OSError:
                break
            i += 1
            s = str(val).lower()
            first = s.strip('"').split()[0] if s else ""
            base = os.path.basename(first)
            if (base in KNOWN_BAD or (s[1:2] == ":" and _drive_removable(s))
                    or "wscript" in base or "cscript" in base):
                findings["run"].append({"name": name, "value": str(val)})
        winreg.CloseKey(key)
    except Exception as e:
        findings["note"] = (findings["note"] + f" Kayıt defteri okunamadı: {e}").strip()

    # Makine geneli kalicilik (HKLM + tum kullanicilar Startup):
    # okumak yonetici istemez, ama SILMEK ister. O yuzden sadece tespit
    # edilir, silme asla otomatik yapilmaz; kullaniciya yol gosterilir.
    try:
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run")
            i = 0
            while True:
                try:
                    name, val, _ = winreg.EnumValue(key, i)
                except OSError:
                    break
                i += 1
                s = str(val).lower()
                first = s.strip('"').split()[0] if s else ""
                base = os.path.basename(first)
                if (base in KNOWN_BAD or base in MASQUERADE_NAMES
                        or "wscript" in base or "cscript" in base):
                    findings["run_machine"].append({"name": name, "value": str(val)})
            winreg.CloseKey(key)
        except Exception:
            pass
        try:
            all_startup = os.path.join(os.environ.get("ProgramData", ""),
                                       r"Microsoft\Windows\Start Menu\Programs\Startup")
            for e in os.listdir(all_startup):
                ln = e.lower()
                if ln in KNOWN_BAD or ln.endswith((".vbs", ".lnk")):
                    findings["startup_machine"].append(os.path.join(all_startup, e))
        except Exception:
            pass
    except Exception:
        pass

    # Gorev Yoneticisi / Kayit Defteri kilidi (Musallat belirtisi)
    try:
        import winreg
        for val in ("DisableTaskMgr", "DisableRegistryTools"):
            try:
                k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\Policies\System")
                data, _ = winreg.QueryValueEx(k, val)
                winreg.CloseKey(k)
                if data == 1:
                    findings["policies"].append(val)
            except FileNotFoundError:
                pass
    except Exception:
        pass

    # Calisan surecler: bilinen zararli adlar + supheli komut satirli
    # wscript/cscript + GERCEK KONUMDA OLMAYAN sistem-taklidi surecler
    # (wuauclt/TrustedInstaller/msiexec/rundll32 Temp'te saklanir)
    try:
        import psutil
        bad_names = {b for b in KNOWN_BAD if b.endswith(".exe")}
        for proc in psutil.process_iter(["pid", "name", "cmdline", "exe"]):
            try:
                name = (proc.info["name"] or "").lower()
                if name in bad_names:
                    findings["processes"].append(
                        {"pid": proc.info["pid"], "name": proc.info["name"], "why": "bilinen zararlı"})
                elif name in ("wscript.exe", "cscript.exe") and _wscript_is_malicious(proc.info.get("cmdline")):
                    findings["processes"].append(
                        {"pid": proc.info["pid"], "name": proc.info["name"], "why": "şüpheli betik çalıştırıyor"})
                elif name in MASQUERADE_NAMES:
                    try:
                        exe = proc.info.get("exe") or ""
                    except Exception:
                        exe = ""
                    if exe and not _is_real_system_process(exe):
                        findings["processes"].append(
                            {"pid": proc.info["pid"], "name": proc.info["name"],
                             "why": "sistem taklidi (gerçek konumda değil)",
                             "filepath": exe})
            except Exception:
                continue
    except Exception:
        pass
    return findings


def _drive_removable(s):
    try:
        import win32file
        letter = s.strip(' "\'')[0].upper()
        return win32file.GetDriveType(f"{letter}:\\") == 2
    except Exception:
        return False


def clean_pc(findings):
    """scan_pc bulgularini kullanici onayiyla kaldirir. Rapor doner."""
    rep = {"removed": [], "errors": []}
    if not findings.get("supported"):
        rep["errors"].append("PC temizliği yalnızca Windows'ta çalışır.")
        return rep
    for proc in findings.get("processes", []):
        try:
            import psutil
            live = psutil.Process(proc["pid"])
            # PID yeniden kullanilmis olabilir: isim eslesmeden oldurme (TOCTOU)
            try:
                if (live.name() or "").lower() != str(proc["name"]).lower():
                    rep["errors"].append(f"{proc['name']} artık çalışmıyor (PID değişmiş), atlandı.")
                    continue
            except Exception:
                rep["errors"].append(f"{proc['name']} doğrulanamadı, atlandı.")
                continue
            live.terminate()
            why = f" — {proc['why']}" if proc.get("why") else ""
            rep["removed"].append(f"İşlem sonlandırıldı: {proc['name']}{why}")
        except Exception as e:
            rep["errors"].append(f"{proc['name']} sonlandırılamadı: {e}")
            continue
        fp = proc.get("filepath") or ""
        if fp and not _is_real_system_process(fp):
            try:
                _safe_remove(fp)
                rep["removed"].append(f"Taklit dosya silindi: {fp}")
            except Exception as e:
                rep["errors"].append(f"{fp} silinemedi: {e}")
    for path in findings.get("temp", []) + findings.get("startup_files", []):
        try:
            _safe_remove(path)
            where = "Geçici" if path in (findings.get("temp") or []) else "Başlangıç"
            rep["removed"].append(f"{where}: {os.path.basename(path)}")
        except Exception as e:
            rep["errors"].append(f"{path} silinemedi: {e}")
    for item in findings.get("startup", []):
        try:
            _safe_remove(item["lnk"])
            rep["removed"].append(f"Başlangıç: {os.path.basename(item['lnk'])}")
        except Exception as e:
            rep["errors"].append(f"{item['lnk']} silinemedi: {e}")
    if findings.get("run"):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_SET_VALUE)
            for item in findings["run"]:
                try:
                    winreg.DeleteValue(key, item["name"])
                    rep["removed"].append(f"Otomatik başlatma: {item['name']}")
                except Exception as e:
                    rep["errors"].append(f"{item['name']} silinemedi: {e}")
            winreg.CloseKey(key)
        except Exception as e:
            rep["errors"].append(f"Kayıt defteri açılamadı: {e}")
    if findings.get("policies"):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                 r"Software\Microsoft\Windows\CurrentVersion\Policies\System",
                                 0, winreg.KEY_SET_VALUE)
            for val in findings["policies"]:
                try:
                    winreg.DeleteValue(key, val)
                    what = ("Görev Yöneticisi kilidi kaldırıldı"
                            if val == "DisableTaskMgr" else "Kayıt Defteri kilidi kaldırıldı")
                    rep["removed"].append(what)
                except Exception as e:
                    rep["errors"].append(f"{val} kaldırılamadı: {e}")
            winreg.CloseKey(key)
        except Exception as e:
            rep["errors"].append(f"İlke anahtarı açılamadı: {e}")
    machine = list(findings.get("run_machine", [])) + list(findings.get("startup_machine", []))
    if machine:
        if is_admin():
            for m in findings.get("run_machine", []):
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                         r"Software\Microsoft\Windows\CurrentVersion\Run",
                                         0, winreg.KEY_SET_VALUE)
                    try:
                        winreg.DeleteValue(key, m["name"])
                        rep["removed"].append(f"Makine otomatik başlatma: {m['name']}")
                    except Exception as e:
                        rep["errors"].append(f"{m['name']} silinemedi: {e}")
                    winreg.CloseKey(key)
                except Exception as e:
                    rep["errors"].append(f"HKLM açılamadı: {e}")
            for f in findings.get("startup_machine", []):
                try:
                    _safe_remove(f)
                    rep["removed"].append(f"Tüm kullanıcılar Başlangıç: {os.path.basename(f)}")
                except Exception as e:
                    rep["errors"].append(f"{f} silinemedi: {e}")
        else:
            rep["errors"].append(
                "Makine geneli kalıcılık bulundu, yönetici yetkisi gerekir: " +
                "; ".join(str(m.get("name", m) if isinstance(m, dict) else m) for m in machine) +
                ". Programı sağ tık → Yönetici olarak çalıştırıp tekrar taratın, "
                "ya da regedit'ten HKLM\\...\\Run anahtarını elle temizleyin.")
    return rep
