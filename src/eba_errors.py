"""EBA hata kataloğu. Kaynak: eta-usb-register 2.0.6 + 1.0.10 + canlı EBA probeları.

CANLI DOGRULANDI (2026-09-30, auth'suz probe):
  EBA.002 Register/Delete -> "Wrong TCKN" / "Tckn does not exist"
  EBA.003 Register sahte  -> "Wrong password" + "MEBBIS üzerinden ... USB Sifresi"
  EBA.004 PwdChanger bos  -> "Wrong authentication code" / "User not found in cache"
  EBA.005 Register bos    -> "Parameter error"
  EBA.101 GetUsbUser      -> "no result" / "EBA ID or USB SERIAL does not exist"
KAYNAKTAN (iki sürümde de aynı, yüksek güven):
  EBA.001 basarı (kaynak yorum + tahta "EBA.001 in text" kontrolü)
  EBA.006 silme -> "USB daha önce eklenmemiş" (1.0.10:727 + 2.0.6:252)
KAYNAKTAN (tek sürüm, orta güven):
  EBA.017 kayıt -> "Gönderdiğiniz bilgileri kontrol ediniz." (yalnız 1.0.10:593)
"""

EBA_URL = "https://giris.eba.gov.tr/EBA_GIRIS/Giris?uygulamaKodu=pardus&login=teacher"
EBA_PASSWORD_RESET_URL = "https://giris.eba.gov.tr/EBA_GIRIS/UsbPasswordChangerV7"
EBA_REGISTER_USB_URL = "https://giris.eba.gov.tr/EBA_GIRIS/RegisterUsbUser"
EBA_DELETE_USB_URL = "https://giris.eba.gov.tr/EBA_GIRIS/DeleteUsbUser"
EBA_ORIGIN = "http://api.etap.org.tr"


def parse_result_code(obj: dict) -> tuple[str, str, str]:
    """(code_suffix, result_code, result_text). Parse guard'lı: split patlamaz."""
    try:
        rc = str(obj.get("resultCode", ""))
        rt = str(obj.get("resultText", ""))
        suffix = rc.split(".")[1] if "." in rc else rc
        return suffix, rc, rt
    except Exception:
        return "", "", ""


# suffix -> (baslik, kullanici_mesaji, aksiyon)
CATALOG: dict[str, tuple[str, str, str]] = {
    "001": ("Başarılı", "", ""),
    "002": (
        "USB oluşturulamaz",
        "TC Kimlik Numarası EBA'da bulunamadı.",
        "Öğretmen hesabıyla EBA'ya giriş yaptığınızdan emin olun.",
    ),
    "003": (
        "USB oluşturulamaz",
        "USB parolası EBA'daki ile eşleşmedi.",
        "Şifre adımını tekrarlayın. Olmadıysa EBA'ya MEBBİS ile girip yeni USB şifresi alın.",
    ),
    "004": (
        "EBA oturumu geçersiz",
        "EBA oturum kodu geçersiz veya süresi dolmuş.",
        "EBA penceresini kapatıp yeniden giriş yapın.",
    ),
    "005": (
        "USB oluşturulamaz",
        "EBA'ya eksik/hatalı parametre gönderildi.",
        "Tekrar deneyin; sürerse log'daki kodu iletin.",
    ),
    "006": (
        "Silinecek kayıt yok",
        "Bu TCKN'ye ait USB kaydı EBA'da yok.",
        "Normal durumdur, işlem yapmanıza gerek yok.",
    ),
    "017": (
        "USB oluşturulamaz",
        "Gönderilen bilgiler EBA tarafından reddedildi.",
        "Kullanıcı adı/parola ve USB seçimini kontrol edip tekrar deneyin.",
    ),
    "101": (
        "Tahtada giriş başarısız olur",
        "EBA ID veya USB seri EBA'da yok.",
        "USB'yi bu uygulamayla yeniden kaydedin.",
    ),
}

GENERIC_REGISTER = (
    "USB oluşturulamaz",
    "USB kaydedilemedi.",
    "Ham sonucu log'dan kopyalayıp tekrar deneyin.",
)
GENERIC_DELETE = (
    "Kayıt silinemedi",
    "USB kaydı silinemedi.",
    "Tekrar deneyin.",
)
NO_CONNECTION = (
    "Bağlantı hatası",
    "EBA'ya ulaşılamadı.",
    "İnterneti, tarih-saati ve güvenlik duvarını kontrol edip tekrar deneyin.",
)


def lookup(suffix: str, fallback: tuple[str, str, str]) -> tuple[str, str, str]:
    return CATALOG.get(suffix, fallback)
