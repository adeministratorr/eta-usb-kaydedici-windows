"""Qt ana pencere. Akis birebir orijinal eta-usb-register 2.0.6 ile ayni:

start -> usb_select -> EBA web -> register (veya silmede dogrudan onay) -> start.

Sayfa isimleri, buton metinleri ve dialog cumleleri orijinal
MainWindow.glade / MainWindow.py'dan alindi. Windows'a ozel ekler
(Flash Dogrula, virus temizligi) ana ekranda ayri bolumde durur.
"""

import os
import sys
import html

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QUrl, QThread, QTimer, Signal, QSettings, QStandardPaths
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

import credentials_manager as CredentialsManager
import eba_client
import eba_errors
import flash_verify
import usb_manager_win
import virus_cleaner
import otp_manager
import sungur_client
import dpapi_win


class Worker(QThread):
    """Genel arka plan iscisi. fn(*args, **kwargs) GUI disi thread'de calisir;
    done(ok, payload) sinyaline bagli slot GUI thread'de calisir.
    Widget'lara sadece slot icinden dokunulur."""

    done = Signal(bool, object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self):
        try:
            payload = self._fn(*self._args, **self._kwargs)
        except Exception as e:
            self.done.emit(False, e)
        else:
            self.done.emit(True, payload)


# --- Qt'ye dokunmayan backend'ler (worker icinde calisir) ---

def _close_session(s):
    try:
        s.close()
    except Exception:
        pass


def _backend_teacher_info(info_url):
    s = eba_client.new_session()
    try:
        return eba_client.get_teacher_info(info_url, session=s)
    finally:
        _close_session(s)


def _backend_register(token, password, teacher, dev):
    """EBA sifre+ kayit + .credentials yazimi. Format anahtarlari aynidir:
    {"eba_id", "username", "usb_serial", "password", "name"}."""
    s = eba_client.new_session()
    try:
        ok, err = eba_client.reset_password(token, password, teacher["tckn"], session=s)
        if not ok:
            return {"ok": False, "stage": "password", "err": err}
        ok, res = eba_client.register_usb(
            teacher["tckn"], password, teacher["eba_id"],
            dev["serial"], teacher["username"], session=s)
        if not ok:
            return {"ok": False, "stage": "register", "err": res}
    finally:
        _close_session(s)
    from passlib.hash import bcrypt
    content = {"eba_id": teacher["eba_id"],
               "username": teacher["username"],
               "usb_serial": dev["serial"],
               "password": bcrypt.hash(password),
               "name": teacher["name"]}
    path = os.path.join(dev["mountpoint"], ".credentials")
    wok, werr = CredentialsManager.save_credentials_file(path, content)
    if wok:
        try:
            virus_cleaner.protect_credentials(path)
        except Exception:
            pass
        return {"ok": True, "path": path}
    home = os.path.expanduser("~")
    fb = os.path.join(home, "1.credentials")
    wok2, _ = CredentialsManager.save_credentials_file(fb, content)
    if wok2:
        return {"ok": True, "fallback": fb, "werr": str(werr)}
    return {"ok": False, "stage": "file", "werr": str(werr), "fb": fb}


def _backend_delete(tckn, mountpoint):
    s = eba_client.new_session()
    try:
        ok, res = eba_client.delete_usb(tckn, session=s)
    finally:
        _close_session(s)
    note = ""
    if ok and mountpoint:
        try:
            fp = os.path.join(mountpoint, ".credentials")
            if os.path.exists(fp):
                try:
                    virus_cleaner.clear_attrs(fp)
                except Exception:
                    pass
                os.remove(fp)
        except Exception as e:
            note = f".credentials silinemedi: {e}"
    return (ok, res, note)


def _backend_verify(dev):
    s = eba_client.new_session()
    try:
        return flash_verify.verify_flash(dev, check_server=True, session=s)
    finally:
        _close_session(s)


def _backend_scan_flash(mp, label):
    return virus_cleaner.scan_flash(mp, volume_label=label)


def _backend_clean_flash(mp, label):
    return virus_cleaner.clean_flash(mp, volume_label=label)


def _backend_scan_pc():
    try:
        import pythoncom
        pythoncom.CoInitialize()
        _com = True
    except Exception:
        _com = False
    try:
        return virus_cleaner.scan_pc()
    finally:
        if _com:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass


def _backend_clean_pc(scan):
    try:
        import pythoncom
        pythoncom.CoInitialize()
        _com = True
    except Exception:
        _com = False
    try:
        return virus_cleaner.clean_pc(scan)
    finally:
        if _com:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass

def _backend_test_sungur(sungur_url, token):
    return sungur_client.check_sungur_connection(sungur_url, token)


def _backend_deploy_otp(sungur_url, token, ebaid, username, secret, full_name, dry_run):
    return sungur_client.deploy_otp_to_sungur(
        base_url=sungur_url,
        token=token,
        ebaid=ebaid,
        username=username,
        secret=secret,
        full_name=full_name,
        dry_run=dry_run
    )


def app_asset(name):
    """PyInstaller onefile (_MEIPASS) + kaynaktan çalıştırma uyumlu asset yolu."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, "assets", name)
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "assets", name)


def app_icon():
    path = app_asset("logo.png")
    return QIcon(path) if os.path.exists(path) else QIcon()


class EbaLoginDialog(QDialog):
    """EBA giris + token yakalama. 2.0.6 on_webview_load_changed karsiligi:
    URL'de 'api' ve 'token=' gorunce token'i al, kapat."""

    login_done = Signal(str, str)  # token, info_url

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("EBA Giriş")
        self.resize(900, 650)
        self.token = ""
        layout = QVBoxLayout(self)
        head = QLabel("EBA Girişi")
        head.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(head)
        sub = QLabel("Aşağıdaki pencereden EBA Hesabınıza giriş yapınız:")
        sub.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout.addWidget(sub)
        self.profile = None
        if not HAS_WEBENGINE:
            msg = QLabel(
                "QtWebEngine kurulu değil. EBA girişi için gerekli.\n\n"
                "Çözüm:\n"
                "pip install PySide6-Addons\n"
                "olmazsa:\n"
                "pip install --force-reinstall PySide6"
            )
            msg.setWordWrap(True)
            msg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
            msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(msg, 1)
            btns = QDialogButtonBox(QDialogButtonBox.Close)
            btns.rejected.connect(self.reject)
            layout.addWidget(btns)
            return

        # Pardus 2.0.6 standard: Configure isolated profile with NoCache and NoPersistentCookies
        try:
            self.profile = QWebEngineProfile(self)
            if hasattr(QWebEngineProfile, "HttpCacheType"):
                self.profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)
            elif hasattr(QWebEngineProfile, "NoCache"):
                self.profile.setHttpCacheType(QWebEngineProfile.NoCache)

            if hasattr(QWebEngineProfile, "PersistentCookiesPolicy"):
                self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies)
            elif hasattr(QWebEngineProfile, "NoPersistentCookies"):
                self.profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)

            self.profile.clearHttpCache()
            self.profile.cookieStore().deleteAllCookies()
            page = QWebEnginePage(self.profile, self)
            self.view = QWebEngineView(self)
            self.view.setPage(page)
        except Exception:
            self.view = QWebEngineView(self)

        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.load(QUrl(eba_errors.EBA_URL))
        self.view.urlChanged.connect(self._on_url)
        layout.addWidget(self.view, 1)

    def _clear_session(self):
        """Clears all session cookies and HTTP cache to prevent account persistence on shared PCs."""
        try:
            if self.profile:
                self.profile.clearHttpCache()
                self.profile.cookieStore().deleteAllCookies()
        except Exception:
            pass

    def _on_url(self, url):
        s = url.toString()
        token = eba_errors.parse_eba_redirect(s)
        if token:
            self.token = token
            self._clear_session()
            self.login_done.emit(token, s)
            self.accept()

    def reject(self):
        self._clear_session()
        super().reject()

    def closeEvent(self, event):
        self._clear_session()
        super().closeEvent(event)


class SungurSettingsDialog(QDialog):
    """Sungur filo yönetim sunucusu adresini ve yönetici token'ını yapılandırma penceresi."""
    def __init__(self, parent=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle("Sungur Sunucu Ayarları")
        self.resize(520, 320)
        self.settings = settings
        layout = QVBoxLayout(self)

        title = QLabel("⚙️ ETAP Sungur Sunucu Yapılandırması")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #1565C0;")
        layout.addWidget(title)

        desc = QLabel(
            "Okul akıllı tahtalarına dinamik OTP anahtarı dağıtmak için kullanılan "
            "merkezi Sungur sunucu adresi ve yönetici erişim token'ını buradan ayarlayabilirsiniz.\n"
            "🌐 MEB FATİH Ağı: İdari Ağ (192.168.0-7.*) ve Etkileşimli Tahta Ağı (10.*) tam uyumludur.\n"
            "Ayarlar 'sungur.ini' dosyasında DPAPI ile güvenle saklanır."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #616161; font-size: 11px;")
        layout.addWidget(desc)

        form = QFormLayout()
        url_layout = QHBoxLayout()
        self.ed_url = QLineEdit(self)
        saved_url = self.settings.value("sungur_url", sungur_client.DEFAULT_SUNGUR_URL) if self.settings else sungur_client.DEFAULT_SUNGUR_URL
        self.ed_url.setText(saved_url)
        self.ed_url.setPlaceholderText("http://192.168.0.67:8080 (İdari Ağ) veya https://192.168.0.67:8443")
        url_layout.addWidget(self.ed_url, 1)

        self.btn_discover = QPushButton("🔎 Ağda Bul")
        self.btn_discover.setToolTip("Ağdaki Sungur sunucusunu ve portunu otomatik keşfet (UDP 7889 ve Multi-Port Taraması)")
        self.btn_discover.clicked.connect(self._do_discover)
        url_layout.addWidget(self.btn_discover)

        form.addRow("Sunucu URL / IP:", url_layout)

        self.ed_candidates = QLineEdit(self)
        saved_cands = self.settings.value("candidate_ips", "") if self.settings else ""
        self.ed_candidates.setText(saved_cands)
        self.ed_candidates.setPlaceholderText("Örn: 192.168.0.67, 192.168.1.50 (Boş ise varsayılanlar kullanılır)")
        self.ed_candidates.setToolTip("Ağ taramasında öncelikle yoklanacak özel idari sunucu IP adresleri (virgülle ayrılmış)")
        form.addRow("Aday IP'ler (Opsiyonel):", self.ed_candidates)

        tok_layout = QHBoxLayout()
        self.ed_token = QLineEdit(self)
        self.ed_token.setEchoMode(QLineEdit.Password)
        raw_token = self.settings.value("sungur_token", "") if self.settings else ""
        saved_token = dpapi_win.unprotect_secret(raw_token)
        self.ed_token.setText(saved_token)
        self.ed_token.setPlaceholderText("Yönetici Token'ı (X-Admin-Token)")
        tok_layout.addWidget(self.ed_token, 1)

        self.btn_toggle_tok = QPushButton("👁 Göster")
        self.btn_toggle_tok.setFixedWidth(80)
        self.btn_toggle_tok.clicked.connect(self._toggle_token_visibility)
        tok_layout.addWidget(self.btn_toggle_tok)

        form.addRow("Yönetici Token:", tok_layout)
        layout.addLayout(form)

        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        layout.addWidget(self.lbl_status)

        btn_row = QHBoxLayout()
        self.btn_test = QPushButton("🔍 Bağlantıyı Test Et")
        self.btn_test.clicked.connect(self._do_test)
        btn_row.addWidget(self.btn_test)
        btn_row.addStretch(1)

        self.btn_save = QPushButton("💾 Kaydet")
        self.btn_save.setStyleSheet("background-color: #2E7D32; color: white; font-weight: bold; padding: 6px 16px;")
        self.btn_save.clicked.connect(self._do_save)
        btn_row.addWidget(self.btn_save)

        self.btn_cancel = QPushButton("İptal")
        self.btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_cancel)

        layout.addLayout(btn_row)

    def _toggle_token_visibility(self):
        if self.ed_token.echoMode() == QLineEdit.Password:
            self.ed_token.setEchoMode(QLineEdit.Normal)
            self.btn_toggle_tok.setText("🔒 Gizle")
        else:
            self.ed_token.setEchoMode(QLineEdit.Password)
            self.btn_toggle_tok.setText("👁 Göster")

    def _do_discover(self):
        hint = self.ed_url.text().strip()
        custom_cands = self.ed_candidates.text().strip()
        if custom_cands and self.settings:
            self.settings.setValue("candidate_ips", custom_cands)
            self.settings.sync()

        self.lbl_status.setStyleSheet("color: #1565C0;")
        self.lbl_status.setText("Ağdaki Sungur sunucusu taranıyor (UDP 7889 & 8443, 8080, 443)...")
        self.btn_discover.setEnabled(False)
        self.btn_test.setEnabled(False)
        QApplication.processEvents()

        w = Worker(sungur_client.discover_sungur_server, timeout=2.5, hint_url=hint)
        self._disc_worker = w
        w.done.connect(self._on_discover_done)
        w.finished.connect(w.deleteLater)
        w.start()

    def _on_discover_done(self, ok, result):
        self.btn_discover.setEnabled(True)
        self.btn_test.setEnabled(True)
        self._disc_worker = None
        if ok and result and isinstance(result, dict):
            found_url = result.get("url", "")
            proto = result.get("protocol", "http").upper()
            port = result.get("port")
            source = "UDP Beacon/Probe" if result.get("source") == "udp_discovery" else "TCP Port Taraması"
            self.ed_url.setText(found_url)
            self.lbl_status.setStyleSheet("color: #2E7D32; font-weight: bold;")
            self.lbl_status.setText(f"✓ Sungur sunucusu bulundu: {found_url} (Port: {port} {proto}, {source})")
        else:
            self.lbl_status.setStyleSheet("color: #E65100; font-weight: bold;")
            self.lbl_status.setText("○ Ağda aktif Sungur sunucusu bulunamadı. Lütfen sunucunun açık ve aynı yerel ağda olduğundan emin olun.")

    def _do_test(self):
        url = self.ed_url.text().strip() or sungur_client.DEFAULT_SUNGUR_URL
        token = self.ed_token.text().strip()
        self.lbl_status.setStyleSheet("color: #1565C0;")
        self.lbl_status.setText("Sungur sunucusu test ediliyor...")
        self.btn_test.setEnabled(False)
        QApplication.processEvents()

        ok, msg, _ = sungur_client.check_sungur_connection(url, token)
        self.btn_test.setEnabled(True)
        if ok:
            self.lbl_status.setStyleSheet("color: #2E7D32; font-weight: bold;")
            self.lbl_status.setText(f"✓ {msg}")
        else:
            self.lbl_status.setStyleSheet("color: #C62828; font-weight: bold;")
            self.lbl_status.setText(f"✗ {msg}")

    def _do_save(self):
        url = self.ed_url.text().strip() or sungur_client.DEFAULT_SUNGUR_URL
        token = self.ed_token.text().strip()
        candidate_ips = self.ed_candidates.text().strip()
        if self.settings:
            self.settings.setValue("sungur_url", url)
            enc_token = dpapi_win.protect_secret(token)
            if enc_token is not None:
                self.settings.setValue("sungur_token", enc_token)
            self.settings.setValue("candidate_ips", candidate_ips)
            self.settings.sync()
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ETA USB Kaydedici")
        self.setWindowIcon(app_icon())
        self.resize(640, 600)
        self.token = ""
        self.teacher = None
        self.mode = "register"  # register, delete
        self.usb = None  # secili cihaz (usb_select sayfasindan gelir)
        self.devices = []
        self._worker = None  # calisan arka plan iscisi (tek seferde bir tane)
        try:
            self._usb_timer = QTimer(self)
            self._usb_timer.setInterval(2000)
            self._usb_timer.timeout.connect(self._auto_refresh_usb)
            self._usb_timer.start()
        except Exception:
            self._usb_timer = None

        self._sungur_probe_worker = None
        try:
            self._sungur_timer = QTimer(self)
            self._sungur_timer.setInterval(12000)
            self._sungur_timer.timeout.connect(self.check_sungur_availability)
            self._sungur_timer.start()
        except Exception:
            self._sungur_timer = None

        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        # Ust bar: Ayarlar ve Hakkinda
        top = QHBoxLayout()
        top.addStretch(1)
        self.btn_sungur_settings = QPushButton("⚙️ Sungur Ayarları")
        self.btn_sungur_settings.setToolTip("Okul Sungur filo yönetim sunucusu IP ve token ayarları")
        self.btn_sungur_settings.clicked.connect(self.show_sungur_settings)
        top.addWidget(self.btn_sungur_settings)

        self.btn_about = QPushButton("Hakkında")
        self.btn_about.clicked.connect(self.show_about)
        top.addWidget(self.btn_about)
        outer.addLayout(top)

        self.stack = QStackedWidget(self)
        outer.addWidget(self.stack, 1)

        # Config file: %APPDATA%/SelcukluMTAL/EtaUsbKaydedici/sungur.ini
        cfg_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not cfg_dir:
            cfg_dir = os.path.join(os.path.expanduser("~"), ".config", "EtaUsbKaydedici")
        os.makedirs(cfg_dir, exist_ok=True)
        ini_path = os.path.join(cfg_dir, "sungur.ini")
        self.settings = QSettings(ini_path, QSettings.IniFormat)

        # One-time migration: If old Windows Registry has settings but ini does not, migrate and clean registry
        try:
            old_reg = QSettings("SelcukluMTAL", "EtaUsbKaydedici")
            if old_reg.contains("sungur_url") and not self.settings.contains("sungur_url"):
                old_url = old_reg.value("sungur_url", "")
                old_tok = old_reg.value("sungur_token", "")
                if old_url:
                    self.settings.setValue("sungur_url", old_url)
                if old_tok:
                    self.settings.setValue("sungur_token", old_tok)
                self.settings.sync()
                old_reg.clear()
        except Exception:
            pass

        self.otp_secret = ""

        self.page_start = self._build_start_page()
        self.page_usb = self._build_usb_page()
        self.page_register = self._build_register_page()
        self.page_spinner = self._build_spinner_page()
        self.page_otp = self._build_otp_page()
        self.stack.addWidget(self.page_start)      # 0: start
        self.stack.addWidget(self.page_usb)        # 1: usb_select
        self.stack.addWidget(self.page_register)   # 2: register
        self.stack.addWidget(self.page_spinner)    # 3: spinner
        self.stack.addWidget(self.page_otp)        # 4: otp

        footer = QLabel("Orijinal Pardus uygulamasından Selçuklu MTAL Bilişim Teknolojileri Alanı tarafından uyarlanmıştır.")
        footer.setAlignment(Qt.AlignCenter)
        outer.addWidget(footer)

        self.show_start()
        try:
            import virus_cleaner as _vc
            if _vc._on_win() and not _vc.is_admin():
                self.log("Not: yönetici modunda çalışmıyor; makine-geneli öğeler salt-okunur listelenir.")
        except Exception:
            pass

    # --- sayfa kurucular (orijinal glade sirasiyla) ---
    def _title(self, text):
        lbl = QLabel(text)
        f = QFont()
        f.setBold(True)
        f.setPointSize(14)
        lbl.setFont(f)
        lbl.setAlignment(Qt.AlignCenter)
        return lbl

    def _build_start_page(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        logo = QLabel()
        pix = QPixmap(app_asset("logo.png"))
        if not pix.isNull():
            logo.setPixmap(pix.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logo.setAlignment(Qt.AlignCenter)
            lay.addWidget(logo)
        lay.addWidget(self._title("ETA USB Kaydedici"))
        sub = QLabel("Yapmak istediğiniz işlemi seçiniz:")
        sub.setAlignment(Qt.AlignCenter)
        lay.addWidget(sub)
        row = QHBoxLayout()
        self.btn_delete = QPushButton("USB'yi EBA Hesabından Sil")
        self.btn_delete.setObjectName("btnDelete")
        self.btn_delete.clicked.connect(self.on_btn_delete_clicked)
        self.btn_register = QPushButton("USB'yi EBA'ya Kaydet ve Hesap Oluştur")
        self.btn_register.clicked.connect(self.on_btn_register_clicked)
        row.addWidget(self.btn_delete)
        row.addWidget(self.btn_register)
        lay.addLayout(row)
        row_otp = QVBoxLayout()
        self.btn_otp = QPushButton("🔑 Okul Tahtalarına OTP (PIN) Tanımla (Sungur)")
        self.btn_otp.setStyleSheet("font-weight: bold; padding: 6px; font-size: 13px;")
        self.btn_otp.setEnabled(False)
        self.btn_otp.setToolTip("Okul ağındaki Sungur sunucusu kontrol ediliyor...")
        self.btn_otp.clicked.connect(self.on_btn_otp_clicked)
        row_otp.addWidget(self.btn_otp)

        self.lbl_otp_status = QLabel("○ Sungur bağlantısı kontrol ediliyor...")
        self.lbl_otp_status.setAlignment(Qt.AlignCenter)
        self.lbl_otp_status.setStyleSheet("color: #757575; font-size: 11px;")
        row_otp.addWidget(self.lbl_otp_status)
        lay.addLayout(row_otp)
        lay.addWidget(self._sep())
        lay.addWidget(QLabel("Bakım:"))
        row2 = QHBoxLayout()
        self.btn_verify = QPushButton("USB Belleği Doğrula")
        self.btn_verify.clicked.connect(self.do_verify)
        self.btn_clean_flash = QPushButton("USB Virüs Temizle")
        self.btn_clean_flash.clicked.connect(self.do_clean_flash)
        self.btn_clean_pc = QPushButton("Bilgisayarı Temizle")
        self.btn_clean_pc.clicked.connect(self.do_clean_pc)
        row2.addWidget(self.btn_verify)
        row2.addWidget(self.btn_clean_flash)
        row2.addWidget(self.btn_clean_pc)
        lay.addLayout(row2)
        self.out = QTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(self.out, 1)
        return pg

    def _build_usb_page(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        top = QHBoxLayout()
        self.btn_back = QPushButton("Geri Dön")
        self.btn_back.clicked.connect(lambda: self.show_start())
        top.addWidget(self.btn_back)
        t = self._title("USB Bellek Seçiniz:")
        top.addWidget(t, 1)
        lay.addLayout(top)
        lay.addWidget(self._sep())
        row = QHBoxLayout()
        self.cmb = QComboBox()
        self.cmb.currentIndexChanged.connect(self.on_cmb_changed)
        self.btn_refresh = QPushButton("Yenile")
        self.btn_refresh.clicked.connect(self.refresh_usb)
        row.addWidget(QLabel("USB:"))
        row.addWidget(self.cmb, 1)
        row.addWidget(self.btn_refresh)
        lay.addLayout(row)
        self.lbl_usb_warn = QLabel("")
        self.lbl_usb_warn.setWordWrap(True)
        lay.addWidget(self.lbl_usb_warn)
        selrow = QHBoxLayout()
        selrow.addStretch(1)
        self.btn_select_usb = QPushButton("Seç")
        self.btn_select_usb.clicked.connect(self.on_btn_select_usb_clicked)
        selrow.addWidget(self.btn_select_usb)
        lay.addLayout(selrow)
        # Silme modunda gorunur (orijinal box_skip_usb_selection)
        self.box_skip = QWidget()
        skip = QVBoxLayout(self.box_skip)
        skip.addWidget(self._sep())
        warn = QLabel("<b>Dikkat:</b> USB Bellek seçmeden devam ederseniz "
                      "sadece EBA'daki kaydınız silinir,\n"
                      "USB içerisindeki şifrelenmiş kayıt dosyası silinmez.")
        warn.setAlignment(Qt.AlignCenter)
        warn.setWordWrap(True)
        skip.addWidget(warn)
        self.btn_skip = QPushButton("USB Seçmeden Devam Et")
        self.btn_skip.clicked.connect(self.on_btn_skip_usb_clicked)
        skip.addWidget(self.btn_skip)
        lay.addWidget(self.box_skip)
        lay.addStretch(1)
        return pg

    def _build_register_page(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.addWidget(self._title("USB Kaydı Oluştur"))
        lay.addWidget(self._sep())
        card = QLabel(
            "• Aşağıdaki kullanıcı adı ve parola bilgisiyle bu "
            "<b>tahta üzerinde bir hesap oluşturulacaktır.</b><br><br>"
            "• USB belleğiniz olmadan da hesabınıza erişebilmek için "
            "<b>parolanızı not etmeyi</b> unutmayınız.<br><br>"
            "• Burada belirlediğiniz parola <b>EBA hesap parolanızı etkilemez.</b><br><br>"
            "• USB anahtar ile tahtada oturum açtığınızda, paneldeki EBA butonu ile "
            "açılacak olan eba.gov.tr de <b>parolasız giriş yapabileceksiniz.</b>"
        )
        card.setWordWrap(True)
        lay.addWidget(card)
        lay.addWidget(self._sep())
        form = QFormLayout()
        self.lbl_username = QLabel("ornek.kullanici")
        form.addRow("Yeni Hesap Adı:", self.lbl_username)
        self.lbl_usb_path = QLabel("")
        self.lbl_usb_path.setWordWrap(True)
        form.addRow("Seçili USB:", self.lbl_usb_path)
        lay.addLayout(form)
        genrow = QHBoxLayout()
        genrow.addStretch(1)
        self.btn_gen = QPushButton("Parola Üret")
        self.btn_gen.clicked.connect(self.gen_pass)
        genrow.addWidget(self.btn_gen)
        self.btn_copy = QPushButton("Kopyala")
        self.btn_copy.setToolTip("Parolayı panoya kopyala")
        self.btn_copy.clicked.connect(self.copy_pass)
        genrow.addWidget(self.btn_copy)
        lay.addLayout(genrow)
        form2 = QFormLayout()
        self.ed_pass = QLineEdit()
        self.ed_pass.setEchoMode(QLineEdit.Password)
        form2.addRow("Yeni Hesap Parolası:", self.ed_pass)
        self.ed_pass2 = QLineEdit()
        self.ed_pass2.setEchoMode(QLineEdit.Password)
        form2.addRow("Yeni Hesap Parolası Tekrar:", self.ed_pass2)
        lay.addLayout(form2)
        self.chk_show = QCheckBox("Parolayı göster")
        self.chk_show.toggled.connect(self.on_show_toggled)
        lay.addWidget(self.chk_show)
        lay.addWidget(self._sep())
        self.btn_register_usb = QPushButton("USB'yi EBA'ya Kaydet ve Hesap Oluştur")
        self.btn_register_usb.clicked.connect(self.on_btn_register_usb_clicked)
        lay.addWidget(self.btn_register_usb)
        lay.addStretch(1)
        return pg

    def _build_spinner_page(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)
        lay.addStretch(1)
        lbl = self._title("Lütfen Bekleyiniz...")
        lay.addWidget(lbl)
        self.lbl_status = QLabel("")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)
        bar = QProgressBar(pg)
        bar.setRange(0, 0)  # indeterminate: islem suresi bilinmiyor
        bar.setTextVisible(False)
        lay.addWidget(bar)
        lay.addStretch(1)
        return pg

    def _build_otp_page(self):
        pg = QWidget()
        lay = QVBoxLayout(pg)

        # Ust bar: Geri Don + Baslik
        top = QHBoxLayout()
        self.btn_otp_back = QPushButton("Geri Dön")
        self.btn_otp_back.clicked.connect(lambda: self.show_start())
        top.addWidget(self.btn_otp_back)
        t = self._title("Okul Tahtalarına OTP (PIN) Tanımla")
        top.addWidget(t, 1)
        lay.addLayout(top)
        lay.addWidget(self._sep())

        # Bilgilendirme Karti
        info_card = QLabel(
            "• Akıllı tahtalarda USB belleğe ihtiyaç duymadan, telefonunuzdaki dinamik "
            "<b>30 saniyelik OTP (PIN) kodu</b> ile oturum açabilirsiniz.<br>"
            "• Bu anahtar yerel ağdaki <b>Sungur Sunucusu</b> aracılığıyla okuldaki tüm tahtaların "
            "<code>/etc/otp-secrets.json</code> dosyasına güvenle dağıtılır."
        )
        info_card.setWordWrap(True)
        lay.addWidget(info_card)

        # Form: Ogretmen Bilgisi + Secret
        form = QFormLayout()
        self.lbl_otp_teacher_info = QLabel("-")
        form.addRow("Öğretmen:", self.lbl_otp_teacher_info)

        row_sec = QHBoxLayout()
        self.lbl_otp_secret_val = QLabel("----------------")
        f_sec = QFont("Courier")
        f_sec.setBold(True)
        f_sec.setPointSize(12)
        self.lbl_otp_secret_val.setFont(f_sec)
        self.lbl_otp_secret_val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row_sec.addWidget(self.lbl_otp_secret_val)

        self.btn_otp_regen = QPushButton("Yeni Anahtar")
        self.btn_otp_regen.clicked.connect(self.regen_otp_secret)
        row_sec.addWidget(self.btn_otp_regen)

        self.btn_otp_copy = QPushButton("Kopyala")
        self.btn_otp_copy.clicked.connect(self.copy_otp_secret)
        row_sec.addWidget(self.btn_otp_copy)
        row_sec.addStretch(1)

        form.addRow("Dinamik OTP Anahtarı:", row_sec)
        lay.addLayout(form)

        # QR Kod ve Telefon Talimati
        mid_row = QHBoxLayout()
        self.lbl_otp_qr = QLabel()
        self.lbl_otp_qr.setFixedSize(160, 160)
        self.lbl_otp_qr.setAlignment(Qt.AlignCenter)
        self.lbl_otp_qr.setStyleSheet("background-color: #ffffff; border: 1px solid #ccc;")
        mid_row.addWidget(self.lbl_otp_qr)

        qr_info = QLabel(
            "<b>Telefon Kurulumu:</b><br><br>"
            "1. Telefonunuzdan <b>Google Authenticator</b>, <b>FreeOTP</b> veya "
            "herhangi bir TOTP uygulamasını açın.<br>"
            "2. <b>+</b> simgesine basıp yandaki QR kodu kamerayla taratın.<br>"
            "3. Uygulamanızda 30 saniyede bir değişen 6 haneli kod üretilecektir."
        )
        qr_info.setWordWrap(True)
        mid_row.addWidget(qr_info, 1)
        lay.addLayout(mid_row)
        lay.addWidget(self._sep())

        # Sungur Yapilandirmasi
        form_sungur = QFormLayout()
        row_srv = QHBoxLayout()
        self.ed_sungur_url = QLineEdit()
        self.ed_sungur_url.setPlaceholderText("http://etap-sungur.local:8080")
        row_srv.addWidget(self.ed_sungur_url, 1)

        self.btn_sungur_test = QPushButton("🔌 Bağlantıyı Test Et")
        self.btn_sungur_test.clicked.connect(self.test_sungur_connection)
        row_srv.addWidget(self.btn_sungur_test)
        form_sungur.addRow("Sungur Sunucu:", row_srv)

        self.ed_sungur_token = QLineEdit()
        self.ed_sungur_token.setEchoMode(QLineEdit.Password)
        self.ed_sungur_token.setPlaceholderText("Sungur X-Admin-Token")
        form_sungur.addRow("Yönetici Parolası:", self.ed_sungur_token)
        lay.addLayout(form_sungur)

        self.lbl_sungur_status = QLabel("")
        self.lbl_sungur_status.setWordWrap(True)
        lay.addWidget(self.lbl_sungur_status)

        # Dagitim Butonlari
        row_act = QHBoxLayout()
        self.btn_otp_dry_run = QPushButton("🔍 Tahtaları Test Et (Dry-Run)")
        self.btn_otp_dry_run.setToolTip("Tahtalara yazmadan bağlantı ve kullanıcı durumunu kontrol eder.")
        self.btn_otp_dry_run.clicked.connect(lambda: self.deploy_otp(dry_run=True))

        self.btn_otp_deploy = QPushButton("🚀 Okuldaki Tüm Tahtalara Dağıt")
        self.btn_otp_deploy.setStyleSheet("font-weight: bold; background-color: #2E7D32; color: white; padding: 6px;")
        self.btn_otp_deploy.clicked.connect(lambda: self.deploy_otp(dry_run=False))

        row_act.addWidget(self.btn_otp_dry_run)
        row_act.addWidget(self.btn_otp_deploy)
        lay.addLayout(row_act)

        # Sonuc / Log Alani
        self.txt_otp_report = QTextEdit()
        self.txt_otp_report.setReadOnly(True)
        self.txt_otp_report.setMaximumHeight(120)
        lay.addWidget(self.txt_otp_report)

        return pg

    def set_spinner_status(self, text):
        """Spinner alt basligi (islem baslamadan GUI'den cagrilir)."""
        try:
            self.lbl_status.setText(text)
        except Exception:
            pass

    def _sep(self):
        from PySide6.QtWidgets import QFrame
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        return f

    # --- yardimcilar ---
    def log(self, t):
        self.out.append(t)

    def _busy(self):
        return self._worker is not None and self._worker.isRunning()

    def _run_bg(self, fn, slot, *args, **kwargs):
        """Worker baslat (GUI kilitlenmez). Mesgulse False doner, tiklama yok sayilir."""
        if self._busy():
            return False
        w = Worker(fn, *args, **kwargs)
        self._worker = w
        w.done.connect(slot)
        w.finished.connect(w.deleteLater)
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
        except Exception:
            pass
        w.start()
        return True

    def _bg_done(self):
        """Her done-slot'un basinda cagrilir: imlec normalize + worker referansi temizlenir."""
        try:
            QApplication.restoreOverrideCursor()
        except Exception:
            pass
        self._worker = None

    def _show_report(self, rows):
        """Bakim sonuclarini renkli gosterir. rows: [(tur, metin)];
        tur: ok/err/warn/info/head. Metinler aynidir, yalnizca renklenir."""
        colors = {"ok": "#2E7D32", "err": "#C62828", "warn": "#E65100",
                  "info": "#1565C0", "head": "#212121"}
        parts = []
        for kind, text in rows:
            c = colors.get(kind, "#212121")
            bold = "font-weight:bold;" if kind in ("ok", "err", "head") else ""
            parts.append(
                f'<div style="color:{c};{bold}">{html.escape(str(text))}</div>')
        try:
            self.out.setHtml("".join(parts))
        except Exception:
            self.out.setPlainText("\n".join(t for _, t in rows))

    def ask(self, title, text):
        return QMessageBox.question(self, title, text,
                                    QMessageBox.Ok | QMessageBox.Cancel) == QMessageBox.Ok

    def info(self, title, msg, action="", detail=""):
        full = msg + (f"\n\nNe yapmalıyım: {action}" if action else "")
        if detail:
            full += f"\n\nDetay: {detail}"
        QMessageBox.information(self, title, full)

    def show_about(self):
        box = QMessageBox(self)
        box.setWindowTitle("Hakkında")
        box.setText(
            "ETA USB Kaydedici (Windows)\n\n"
            "Pardus eta-usb-register 2.0.6 Windows portu (GPL-3.0+).\n"
            "USB'nizi EBA Hesabınıza kolayca kaydedin.\n\n"
            "Orijinal Pardus uygulamasından Selçuklu MTAL "
            "Bilişim Teknolojileri Alanı tarafından uyarlanmıştır.",
        )
        pix = QPixmap(app_asset("logo.png"))
        if not pix.isNull():
            box.setIconPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        box.exec()

    def show_sungur_settings(self):
        """Açar ve kullanıcıdan Sungur filo sunucusu URL ve token ayarlarını alır."""
        dlg = SungurSettingsDialog(self, self.settings)
        if dlg.exec() == QDialog.Accepted:
            self.check_sungur_availability()
            if hasattr(self, "ed_sungur_url") and hasattr(self, "ed_sungur_token"):
                self.ed_sungur_url.setText(self.settings.value("sungur_url", sungur_client.DEFAULT_SUNGUR_URL))
                raw_tok = self.settings.value("sungur_token", "")
                self.ed_sungur_token.setText(dpapi_win.unprotect_secret(raw_tok))

    def show_start(self):
        self.stack.setCurrentIndex(0)
        self.check_sungur_availability()
        self._check_leftover_credentials()

    def _check_leftover_credentials(self):
        """Uygulama ana ekranındayken ev dizininde sahipsiz 1.credentials kalıp kalmadığını denetler."""
        if getattr(self, "_credentials_cleanup_prompted", False):
            return
        home_fb = os.path.join(os.path.expanduser("~"), "1.credentials")
        if os.path.exists(home_fb):
            self._credentials_cleanup_prompted = True
            ans = QMessageBox.question(
                self,
                "Geçici Dosya Temizliği",
                "Ev dizininde ('~/1.credentials') daha önce USB oluşturulurken kaydedilmiş geçici kimlik dosyası bulundu.\n\n"
                "Bu dosya şifrelenmiş EBA kimlik bilgilerinizi içerir ve ortak bilgisayarlarda güvenlik riski oluşturabilir.\n\n"
                "USB belleğinize kopyaladıysanız, güvenlik nedeniyle bu geçici dosya silinsin mi?",
                QMessageBox.Yes | QMessageBox.No
            )
            if ans == QMessageBox.Yes:
                try:
                    os.remove(home_fb)
                    self.log("Ev dizinindeki sahipsiz '1.credentials' dosyası temizlendi.")
                except Exception as e:
                    self.log(f"1.credentials silinemedi: {e}")

    def check_sungur_availability(self):
        """Arka planda Sungur sunucusunun yerel agda aktif olup olmadigini sorgular."""
        if self._sungur_probe_worker is not None and self._sungur_probe_worker.isRunning():
            return
        if self.stack.currentIndex() != 0:
            return

        saved_url = self.settings.value("sungur_url", sungur_client.DEFAULT_SUNGUR_URL)
        w = Worker(sungur_client.is_sungur_online, saved_url)
        self._sungur_probe_worker = w
        w.done.connect(self._on_sungur_availability_done)
        w.finished.connect(w.deleteLater)
        w.start()

    def _on_sungur_availability_done(self, ok, is_online):
        self._sungur_probe_worker = None
        if ok and is_online:
            self.btn_otp.setEnabled(True)
            self.btn_otp.setToolTip("Sungur sunucusu aktif. Okul tahtalarına dinamik OTP tanımlayabilirsiniz.")
            self.lbl_otp_status.setStyleSheet("color: #2E7D32; font-size: 11px; font-weight: bold;")
            self.lbl_otp_status.setText("● Okul ağı aktif — Sungur sunucusuna bağlandı")
        else:
            self.btn_otp.setEnabled(False)
            self.btn_otp.setToolTip(
                "Okul yerel ağında Sungur sunucusuna ulaşılamadı.\n"
                "Tahtalara OTP tanımlamak için okulun yerel ağına bağlı olmalısınız."
            )
            self.lbl_otp_status.setStyleSheet("color: #C62828; font-size: 11px;")
            self.lbl_otp_status.setText("○ Sungur bulunamadı (Bu özellik yalnızca okul yerel ağında kullanılabilir)")

    # --- start sayfasi ---
    def on_btn_delete_clicked(self):
        self.mode = "delete"
        self.usb = None
        self.box_skip.setVisible(True)
        self.refresh_usb()
        self.stack.setCurrentIndex(1)

    def on_btn_register_clicked(self):
        self.mode = "register"
        self.usb = None
        self.box_skip.setVisible(False)
        self.refresh_usb()
        self.stack.setCurrentIndex(1)

    def on_btn_otp_clicked(self):
        self.mode = "otp"
        self.usb = None
        self.open_eba_login()

    # --- usb_select sayfasi ---
    def refresh_usb(self):
        self._fill_usb_combo(usb_manager_win.list_usb_devices_win(), None)

    @staticmethod
    def _usb_key(d):
        return ((d or {}).get("mountpoint") or "", (d or {}).get("serial") or "")

    def _fill_usb_combo(self, devs, keep_key):
        self.devices = devs or []
        self.cmb.blockSignals(True)
        self.cmb.clear()
        for d in self.devices:
            self.cmb.addItem(f"{d.get('label')} — {d.get('mountpoint')} [{d.get('serial')}] ({d.get('fstype')})")
        self.cmb.blockSignals(False)
        if self.devices:
            idx = 0
            if keep_key:
                for j, d in enumerate(self.devices):
                    if self._usb_key(d) == keep_key:
                        idx = j
                        break
            self.cmb.setCurrentIndex(idx)
            self.on_cmb_changed(idx)
        else:
            try:
                self.lbl_usb_warn.setStyleSheet("")
            except Exception:
                pass
            self.lbl_usb_warn.setText("USB bulunamadı. USB belleği takıp Yenile'ye basın.")
            self.btn_select_usb.setEnabled(False)

    def _auto_refresh_usb(self):
        """Tak/çıkar algılama: yalnız USB sayfasında, meşgul değilken ve
        modal dialog yokken; liste değiştiyse seçimi koruyarak yeniler."""
        try:
            if self._busy():
                return
            if self.stack.currentIndex() != 1:
                return
            if QApplication.activeModalWidget() is not None:
                return
            devs = usb_manager_win.list_usb_devices_win()
        except Exception:
            return
        try:
            old_sig = [self._usb_key(d) for d in (self.devices or [])]
            new_sig = [self._usb_key(d) for d in (devs or [])]
            if old_sig == new_sig:
                return
            i = self.cmb.currentIndex()
            keep = self._usb_key(self.devices[i]) if 0 <= i < len(self.devices) else None
            self._fill_usb_combo(devs, keep)
        except Exception:
            pass

    @staticmethod
    def _ready_badge(dev):
        fstype = ((dev or {}).get("fstype") or "").upper()
        try:
            import psutil
            total = psutil.disk_usage((dev or {}).get("mountpoint") or "").total
            mid = f" — {total / 1_000_000_000:.1f} GB"
        except Exception:
            mid = ""
        return f"✓ Hazır{mid} — {fstype}"

    def on_cmb_changed(self, i):
        dev = self.devices[i] if 0 <= i < len(self.devices) else None
        if not dev:
            self.lbl_usb_warn.setText("USB bulunamadı. USB belleği takıp Yenile'ye basın.")
            self.btn_select_usb.setEnabled(False)
            return
        # EBA girisine sokmadan bastan ele: seri/format/yazilabilirlik burada belli olsun
        ok, title, msg = usb_manager_win.preflight(dev)
        if not ok:
            try:
                self.lbl_usb_warn.setStyleSheet("color: #C62828;")
            except Exception:
                pass
            self.lbl_usb_warn.setText(f"{title}: {msg}")
            self.btn_select_usb.setEnabled(False)
        else:
            try:
                self.lbl_usb_warn.setStyleSheet("color: #2E7D32; font-weight: bold;")
            except Exception:
                pass
            self.lbl_usb_warn.setText(self._ready_badge(dev))
            self.btn_select_usb.setEnabled(True)

    def on_btn_select_usb_clicked(self):
        i = self.cmb.currentIndex()
        dev = self.devices[i] if 0 <= i < len(self.devices) else None
        ok, title, msg = usb_manager_win.preflight(dev or {})
        if not ok:
            self.info(title, msg)
            return
        self.usb = dev
        self.open_eba_login()

    def on_btn_skip_usb_clicked(self):
        self.usb = None
        self.open_eba_login()

    # --- EBA web sayfasi ---
    def open_eba_login(self):
        dlg = EbaLoginDialog(self)
        dlg.login_done.connect(self._on_token)
        if dlg.exec() == QDialog.Accepted and dlg.token:
            return
        # Pencere kapatildi, giris yapilmadi -> usb_select sayfasinda kal
        if not self.token:
            self.stack.setCurrentIndex(1)

    def _on_token(self, token, info_url):
        self.token = token
        self.set_spinner_status("EBA öğretmen bilgileri doğrulanıyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_teacher_info, self._on_teacher_done, info_url)

    def _on_teacher_done(self, ok, payload):
        self._bg_done()
        if not ok:
            self.info("Bağlantı hatası", "EBA'ya ulaşılamadı.",
                      "İnterneti, tarih-saati ve güvenlik duvarını kontrol edip tekrar deneyin.",
                      detail=str(payload))
            self.token = ""
            self.stack.setCurrentIndex(0)
            return
        ok2, data = payload
        if not ok2:
            self.info(data["title"], data["message"], data.get("action", ""), data.get("detail", ""))
            self.token = ""
            self.stack.setCurrentIndex(0)
            return
        self.teacher = data
        if self.mode == "delete":
            if self.ask("Emin misiniz?",
                        "EBA'daki Akıllı Tahta USB ile giriş kaydınız silinecek."):
                if self.delete_usb_record():
                    return
            self.token = ""
            self.show_start()
        elif self.mode == "otp":
            self.log(f"EBA girişi (OTP Modu): {data['name']} ({data['username']})")
            self.setup_otp_page()
            self.stack.setCurrentIndex(4)  # otp page
        else:
            self.lbl_username.setText(data["username"])
            u = self.usb or {}
            self.lbl_usb_path.setText(f"{u.get('label', '')} - {u.get('mountpoint', '')} [{u.get('serial', '')}]")
            self.ed_pass.clear()
            self.ed_pass2.clear()
            self.chk_show.setChecked(False)
            self.log(f"EBA girişi: {data['name']} ({data['username']})")
            self.stack.setCurrentIndex(2)  # register

    # --- register sayfasi ---
    def gen_pass(self):
        p = CredentialsManager.generate_random_password()
        self.ed_pass.setText(p)
        self.ed_pass2.setText(p)

    def _clear_clipboard_if_matches(self, text):
        """Clears system clipboard after timeout if it still contains the sensitive password/secret."""
        try:
            cb = QApplication.clipboard()
            if cb and cb.text() == text:
                cb.clear()
        except Exception:
            pass

    def copy_pass(self):
        p = self.ed_pass.text()
        if not p:
            self.info("Uyarı", "Kopyalanacak parola yok. Önce Parola Üret'e basın.")
            return
        try:
            QApplication.clipboard().setText(p)
            QTimer.singleShot(30000, lambda t=p: self._clear_clipboard_if_matches(t))
        except Exception:
            return
        try:
            self.btn_copy.setText("Kopyalandı ✓ (30 sn)")
            QTimer.singleShot(1500, lambda: self.btn_copy.setText("Kopyala"))
        except Exception:
            pass

    def on_show_toggled(self, checked):
        m = QLineEdit.Normal if checked else QLineEdit.Password
        self.ed_pass.setEchoMode(m)
        self.ed_pass2.setEchoMode(m)

    def on_btn_register_usb_clicked(self):
        if self.ed_pass.text() != self.ed_pass2.text():
            self.info("Uyarı", "Parolalar aynı değil.")
            return
        if self.ed_pass.text() == "":
            self.info("Uyarı", "Parola boş olamaz.")
            return
        if not self.ask(
            "Emin misiniz?",
            "Yazdığınız kullanıcı adı ve parola bilgisiyle bu "
            "tahta üzerinde bir hesap oluşturulacaktır.\n\n"
            "USB Belleğiniz olmadan da hesabınıza erişebilmek için "
            "parolanızı not etmeyi unutmayınız.\n\n"
            "Hesabınız EBA'ya kaydedilecektir, USB belleği kullanarak "
            "hesabınıza giriş yapabilirsiniz.",
        ):
            return
        self.register_usb()

    def register_usb(self):
        p1 = self.ed_pass.text()
        if not p1:
            self.info("Başarısız!", "Parola girmeyi unutmayınız.")
            return
        if not self.teacher or not self.teacher.get("username"):
            self.info("Başarısız!",
                      "Kullanıcı Adı bilgisi eksik. EBA'ya giriş yaptığınızdan emin olunuz.")
            return
        dev = dict(self.usb or {})
        ok, title, msg = usb_manager_win.preflight(dev)
        if not ok:
            self.info(title, msg)
            return
        teacher = dict(self.teacher)
        token = self.token
        self.log("Şifre EBA'ya gönderiliyor...")
        self.set_spinner_status("USB belleğe güvenlik anahtarı oluşturuluyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_register, self._on_register_done,
                     token, p1, teacher, dev)

    def _on_register_done(self, ok, payload):
        self._bg_done()
        if not ok:
            self.info("Bağlantı hatası", "EBA'ya ulaşılamadı.",
                      "İnterneti, tarih-saati ve güvenlik duvarını kontrol edip tekrar deneyin.",
                      detail=str(payload))
            self.stack.setCurrentIndex(2)
            return
        if not payload.get("ok"):
            stage = payload.get("stage")
            if stage in ("password", "register"):
                err = payload.get("err") or {}
                self.info(err.get("title", "Başarısız!"), err.get("message", ""),
                          err.get("action", ""), err.get("detail", ""))
            else:
                self.info("Başarısız!",
                          f"Hesap bilgileri, USB'ye veya Ev dizinine('{payload.get('fb')}') kaydedilemedi.Hata:\n\n{payload.get('werr')}")
            self.stack.setCurrentIndex(2)
            return
        if payload.get("fallback"):
            self.info("Dikkat! Güvenlik Riski — Geçici Dosya Oluşturuldu",
                      "Hesap bilgileri, USB belleğe doğrudan yazılamadığı için Ev dizinine '1.credentials' ismiyle geçici olarak kaydedildi.\n\n"
                      "⚠️ GÜVENLİK UYARISI: Bu dosya şifrelenmiş kimlik bilgilerinizi içerir. Dosyayı USB belleğinizin ana dizinine kopyalayıp adını '.credentials' yaptıktan sonra, ev dizinindeki '1.credentials' dosyasını MUTLAKA SİLİN!",
                      detail=str(payload.get("werr")))
        else:
            self.info("Başarılı",
                      "EBA Hesabınızdaki USB Kaydı yenilendi ve yeni USB'nize kaydedildi.")
            self.log(f"Yazıldı: {payload.get('path')}")
        self.token = ""
        self.show_start()

    # --- sil ---
    def delete_usb_record(self):
        if not self.teacher or not self.teacher.get("tckn"):
            self.info("TC Kimlik No bulunamadı", "EBA'ya giriş yaptığınızdan emin olun.")
            return False
        tckn = self.teacher.get("tckn")
        mp = (self.usb or {}).get("mountpoint") if self.usb else ""
        self.set_spinner_status("EBA USB kaydı siliniyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_delete, self._on_delete_done, tckn, mp or "")
        return True

    def _on_delete_done(self, ok, payload):
        self._bg_done()
        if not ok:
            self.info("Bağlantı hatası", "EBA'ya ulaşılamadı.",
                      "İnterneti, tarih-saati ve güvenlik duvarını kontrol edip tekrar deneyin.",
                      detail=str(payload))
            self.token = ""
            self.show_start()
            return
        ok2, res, note = payload
        if ok2:
            if note:
                self.log(note)
            self.info("Başarılı", "EBA Hesabınızdaki USB Kaydı silindi.")
        elif (res or {}).get("not_found"):
            self.info("Başarısız!", "USB daha önce eklenmemiş.")
        else:
            res = res or {}
            self.info(res.get("title", "Kayıt silinemedi"), res.get("message", ""),
                      res.get("action", ""), res.get("detail", ""))
        self.token = ""
        self.show_start()

    # --- bakim (Windows ekleri, ana ekranda) ---
    def pick_tool_device(self):
        devs = usb_manager_win.list_usb_devices_win()
        if not devs:
            self.info("USB bulunamadı", "USB belleği takıp tekrar deneyin.")
            return None
        if len(devs) == 1:
            return devs[0]
        items = [f"{d.get('label')} — {d.get('mountpoint')} [{d.get('serial')}] ({d.get('fstype')})"
                 for d in devs]
        item, ok = QInputDialog.getItem(self, "USB seçin", "USB:", items, 0, False)
        if not ok:
            return None
        return devs[items.index(item)]

    def do_verify(self):
        dev = self.pick_tool_device()
        if not dev:
            return
        self.set_spinner_status("USB bellek doğrulanıyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_verify, self._on_verify_done, dict(dev))

    def _on_verify_done(self, ok, payload):
        self._bg_done()
        self.show_start()
        if not ok:
            self.info("Bağlantı hatası", "Doğrulama yapılamadı.",
                      "Tekrar deneyin.", detail=str(payload))
            return
        res = payload
        o = res["owner"]
        rows = []
        if o:
            rows.append(("head", f"Sahip: {o['name']} ({o['username']})"))
            rows.append(("head", f"Seri: {o['usb_serial']} | EBA ID: {o['eba_id_masked']}"))
        for name, good, msg in res["checks"]:
            if good in ("skipped", "warn"):
                rows.append(("warn", f"⚠️ {name}: {msg}"))
            elif good:
                rows.append(("ok", f"✓ {name}: {msg}"))
            else:
                rows.append(("err", f"✗ {name}: {msg}"))
        if res["ok"]:
            rows.append(("ok", "Sonuç: Bu flash tahtada çalışır."))
        else:
            rows.append(("err", "Sonuç: Bu flash TAHTADA ÇALIŞMAZ — yukarıdaki ✗ satırına bakın."))

        # Check and cleanup temporary ~/1.credentials if it was left behind
        home_fb = os.path.join(os.path.expanduser("~"), "1.credentials")
        if os.path.exists(home_fb):
            del_fb = QMessageBox.question(
                self,
                "Geçici Dosya Temizliği",
                "Ev dizininde '1.credentials' dosyası bulundu.\n\n"
                "USB doğrulaması yapıldığına göre, güvenlik riski oluşturan bu geçici dosya silinsin mi?",
                QMessageBox.Yes | QMessageBox.No
            )
            if del_fb == QMessageBox.Yes:
                try:
                    os.remove(home_fb)
                    self.log("Ev dizinindeki geçici 1.credentials silindi.")
                    rows.append(("ok", "Ev dizinindeki geçici '1.credentials' silindi."))
                except Exception as e:
                    self.log(f"1.credentials silinemedi: {e}")

        rows.append(("info", "Not: USB'yi tahtada giriş ekranındayken takın."))
        self._show_report(rows)

    def do_clean_flash(self):
        dev = self.pick_tool_device()
        if not dev:
            return
        mp = dev.get("mountpoint") or ""
        self.set_spinner_status("Virüs ve sahte kısayollar taranıyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_scan_flash, self._on_flash_scan_done,
                     mp, dev.get("label") or "")

    def _on_flash_scan_done(self, ok, payload):
        self._bg_done()
        self.show_start()
        if not ok:
            self.info("USB oluşturulamaz", "Tarama yapılamadı.",
                      detail=str(payload))
            return
        scan = payload
        if scan["error"]:
            self.info("USB oluşturulamaz", scan["error"])
            return
        n_bad = (len(scan["bad_exes"]) + len(scan["shortcut_hits"])
                  + len(scan["orphan_lnks"]) + (1 if scan["autorun"] else 0)
                  + len(scan.get("folder_clones", []))
                  + len(scan.get("sub_lnks", [])) + len(scan.get("sub_infs", [])))
        detail = []
        if scan["autorun"]:
            detail.append("• autorun.inf")
        detail += [f"• {b}" for b in scan["bad_exes"]]
        detail += [f"• {c} (klasör taklidi .exe, silinecek)" for c in scan.get("folder_clones", [])]
        detail += [f"• {h['lnk']} (→ {h['folder']} klasörünün sahte kısayolu)" for h in scan["shortcut_hits"]]
        detail += [f"• {l} (sahipsiz kısayol, silinecek)" for l in scan["orphan_lnks"]]
        detail += [f"• {l} (alt klasör kısayolu, silinecek)" for l in scan.get("sub_lnks", [])]
        detail += [f"• {l} (alt klasör inf, silinecek)" for l in scan.get("sub_infs", [])]
        detail += [f"• gizli: {h}" for h in scan["hidden"]]
        for st in scan["stash"]:
            inside = ", ".join(st["items"][:5]) + ("…" if len(st["items"]) > 5 else "")
            kind = "sürücü etiketli" if st.get("why") == "etiket" else "isimsiz"
            detail.append(f"• '{st['folder']}' ({kind} zulalama) içine taşınmış {len(st['items'])} öğe ({inside}) → köke iade edilecek")
        if scan["orphan_lnks"] or scan["suspicious"]:
            detail.append(f"• bilinmeyen .exe — silinmeyecek, elle bakın: {', '.join(scan['suspicious'])}" if scan["suspicious"] else "")
            detail = [d for d in detail if d]
        if n_bad == 0 and not scan["hidden"] and not scan["stash"]:
            self.info("Temiz", "USB'de bilinen virüs izi yok.")
            return
        if not self.ask("Virüs temizlensin mi?",
                        f"{n_bad} zararlı öğe bulundu:\n" + "\n".join(detail) +
                        "\n\nBunlar silinip gizlenenler geri açılacak, zulalama klasöründekiler ve .credentials köke iade edilecek."):
            return
        self.set_spinner_status("Bulunan zararlılar temizleniyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_clean_flash, self._on_flash_clean_done,
                     scan.get("root") or "", scan.get("label") or "")

    def _on_flash_clean_done(self, ok, payload):
        self._bg_done()
        self.show_start()
        if not ok:
            self.info("USB oluşturulamaz", "Temizlik yapılamadı.",
                      detail=str(payload))
            return
        rep = payload
        rows = [(("ok", f"Silindi: {', '.join(rep['removed'])}") if rep["removed"] else ("info", "Silinen: yok"))]
        if rep["unhidden"]:
            rows.append(("ok", f"Geri açıldı: {', '.join(rep['unhidden'])}"))
        if rep["restored_items"]:
            rows.append(("ok", "Köke iade edildi:"))
            rows += [("ok", f"  • {m}") for m in rep["restored_items"]]
        if rep["restored"]:
            rows.append(("ok", rep["restored"]))
        if rep["kept"]:
            rows.append(("warn", f"Ellemedim (elle bakın): {', '.join(rep['kept'])}"))
        if rep["errors"]:
            rows.append(("err", "Hatalar: " + "; ".join(rep["errors"])))
        rows.append(("info", "Sonraki adım: USB Belleği Doğrula'ya basıp sahibini kontrol edin."))
        self._show_report(rows)

    def do_clean_pc(self):
        self.set_spinner_status("Bilgisayar taranıyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_scan_pc, self._on_pc_scan_done)

    def _on_pc_scan_done(self, ok, payload):
        self._bg_done()
        self.show_start()
        if not ok:
            self.info("Desteklenmiyor", "Tarama yapılamadı.", detail=str(payload))
            return
        scan = payload
        if not scan.get("supported"):
            self.info("Desteklenmiyor", scan.get("note", "PC temizliği yalnızca Windows'ta çalışır."))
            return
        items = ([f"Başlangıç: {s['lnk']} → {s['target']}" for s in scan["startup"]] +
                 [f"Başlangıç dosyası: {f}" for f in scan.get("startup_files", [])] +
                 [f"Geçici: {f}" for f in scan.get("temp", [])] +
                 [f"Otomatik başlatma: {r['name']} → {r['value']}" for r in scan["run"]] +
                 [f"Kilitli: {p} (Görev Yöneticisi/Kayıt Defteri kilidi kaldırılacak)" for p in scan.get("policies", [])] +
                 [f"Çalışan zararlı: {p['name']} (sonlandırılacak)" for p in scan.get("processes", [])] +
                 [f"MAKİNE GENELİ (yönetici modunda silinir): {r['name']} → {r['value']}" for r in scan.get("run_machine", [])] +
                 [f"MAKİNE GENELİ (yönetici modunda silinir): {f}" for f in scan.get("startup_machine", [])])
        if not items:
            self.info("Temiz", "Bilgisayarda bilinen virüs izi yok.\nNot: tam güvence için Windows Defender ile Tam Tarama önerilir.")
            return

        has_machine = bool(scan.get("run_machine") or scan.get("startup_machine"))
        if has_machine and not virus_cleaner.is_admin():
            elevate_choice = QMessageBox.question(
                self,
                "Yönetici İzni Gerekli",
                "Makine-geneli (HKLM veya Ortak Başlangıç) virüs kalıntıları tespit edildi.\n\n"
                "Bunların temizlenebilmesi için Yönetici (UAC) yetkisi gerekmektedir.\n\n"
                "Uygulama Yönetici Olarak yeniden başlatılsın mı?",
                QMessageBox.Yes | QMessageBox.No
            )
            if elevate_choice == QMessageBox.Yes:
                virus_cleaner.ensure_admin()
                return

        if not self.ask("Bunlar kaldırılsın mı?", "Şüpheli kayıtlar:\n" + "\n".join(items)):
            return
        self.set_spinner_status("Bulunan zararlılar kaldırılıyor...")
        self.stack.setCurrentIndex(3)  # spinner
        self._run_bg(_backend_clean_pc, self._on_pc_clean_done, scan)

    def _on_pc_clean_done(self, ok, payload):
        self._bg_done()
        self.show_start()
        if not ok:
            self.info("Desteklenmiyor", "Temizlik yapılamadı.", detail=str(payload))
            return
        rep = payload
        rows = [(("ok", f"Kaldırıldı: {', '.join(rep['removed'])}") if rep["removed"] else ("info", "Kaldırılan: yok"))]
        if rep["errors"]:
            rows.append(("err", "Hatalar: " + "; ".join(rep["errors"])))
        rows.append(("info", "Önemli: temizlikten sonra bilgisayarı yeniden başlatın."))
        self._show_report(rows)

    # --- OTP ve Sungur Dagitim Metotlari ---
    def setup_otp_page(self):
        """EBA girisinden sonra OTP sayfasini hazirlar."""
        if not self.teacher:
            return
        name = self.teacher.get("name", "")
        uname = self.teacher.get("username", "")
        ebaid = self.teacher.get("eba_id", "")
        self.lbl_otp_teacher_info.setText(
            f"<b>{html.escape(name)}</b> ({html.escape(uname)}) — EBA ID: {html.escape(str(ebaid))}"
        )

        saved_url = self.settings.value("sungur_url", sungur_client.DEFAULT_SUNGUR_URL)
        raw_token = self.settings.value("sungur_token", "")
        saved_token = dpapi_win.unprotect_secret(raw_token)
        self.ed_sungur_url.setText(saved_url)
        self.ed_sungur_token.setText(saved_token)
        self.lbl_sungur_status.setText("")
        self.txt_otp_report.clear()

        self.regen_otp_secret()

    def regen_otp_secret(self):
        self.otp_secret = otp_manager.generate_otp_secret()
        self.lbl_otp_secret_val.setText(self.otp_secret)
        self._update_otp_qr()

    def _update_otp_qr(self):
        if not self.teacher or not self.otp_secret:
            return
        uname = self.teacher.get("username", "kullanici")
        otp_url = otp_manager.get_otp_auth_url(username=uname, secret=self.otp_secret)
        pix, err = otp_manager.generate_qr_image(otp_url)
        if pix and not pix.isNull():
            self.lbl_otp_qr.setPixmap(pix.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.lbl_otp_qr.setText(f"QR Hatası:\n{err or 'Oluşturulamadı'}")

    def copy_otp_secret(self):
        sec = getattr(self, "otp_secret", "")
        if not sec:
            return
        try:
            QApplication.clipboard().setText(sec)
            QTimer.singleShot(30000, lambda t=sec: self._clear_clipboard_if_matches(t))
            self.btn_otp_copy.setText("Kopyalandı ✓ (30 sn)")
            QTimer.singleShot(1500, lambda: self.btn_otp_copy.setText("Kopyala"))
        except Exception:
            pass

    def test_sungur_connection(self):
        url = self.ed_sungur_url.text().strip() or sungur_client.DEFAULT_SUNGUR_URL
        token = self.ed_sungur_token.text().strip()
        self.settings.setValue("sungur_url", url)
        enc_token = dpapi_win.protect_secret(token)
        if enc_token is not None:
            self.settings.setValue("sungur_token", enc_token)
        self.settings.sync()

        self.lbl_sungur_status.setStyleSheet("color: #1565C0;")
        self.lbl_sungur_status.setText("Sungur sunucusu test ediliyor...")
        self.btn_sungur_test.setEnabled(False)

        self._run_bg(_backend_test_sungur, self._on_sungur_test_done, url, token)

    def _on_sungur_test_done(self, ok, payload):
        self._bg_done()
        self.btn_sungur_test.setEnabled(True)
        if not ok:
            self.lbl_sungur_status.setStyleSheet("color: #C62828; font-weight: bold;")
            self.lbl_sungur_status.setText(f"Bağlantı Hatası: {payload}")
            return

        conn_ok, msg, drift_data = payload
        if conn_ok:
            self.lbl_sungur_status.setStyleSheet("color: #2E7D32; font-weight: bold;")
            self.lbl_sungur_status.setText(f"✓ {msg}")
        else:
            self.lbl_sungur_status.setStyleSheet("color: #C62828; font-weight: bold;")
            self.lbl_sungur_status.setText(f"✗ {msg}")

    def deploy_otp(self, dry_run=False):
        if not self.teacher or not self.teacher.get("eba_id"):
            self.info("Hata", "EBA öğretmen bilgileri eksik. Lütfen tekrar giriş yapınız.")
            return

        url = self.ed_sungur_url.text().strip() or sungur_client.DEFAULT_SUNGUR_URL
        token = self.ed_sungur_token.text().strip()
        self.settings.setValue("sungur_url", url)
        enc_token = dpapi_win.protect_secret(token)
        if enc_token is not None:
            self.settings.setValue("sungur_token", enc_token)
        self.settings.sync()

        action_name = "Tahtaları Test Etme (Dry-Run)" if dry_run else "Tüm Tahtalara OTP Dağıtımı"
        warning = (
            "Okuldaki tüm akıllı tahtalar test edilecek ve kullanıcı durumları raporlanacaktır.\n\nDevam edilsin mi?"
            if dry_run else
            "Yeni OTP (PIN) anahtarınız okuldaki tüm akıllı tahtalara tanımlanacaktır.\n\n"
            "Telefonunuzdaki uygulamanın bu anahtarı taradığından emin misiniz?\n\nDevam edilsin mi?"
        )
        if not self.ask(action_name, warning):
            return

        ebaid = str(self.teacher.get("eba_id", ""))
        uname = self.teacher.get("username", "")
        fname = self.teacher.get("name", "")
        secret = self.otp_secret

        status_text = "Sungur üzerinden tahtalar test ediliyor..." if dry_run else "Sungur üzerinden tahtalara OTP dağıtılıyor..."
        self.set_spinner_status(status_text)
        self.stack.setCurrentIndex(3)  # spinner

        self._run_bg(
            _backend_deploy_otp,
            lambda ok, res: self._on_deploy_done(ok, res, dry_run),
            url, token, ebaid, uname, secret, fname, dry_run
        )

    def _on_deploy_done(self, ok, payload, dry_run):
        self._bg_done()
        self.stack.setCurrentIndex(4)  # otp page

        if not ok:
            self.info("Dağıtım Hatası", "Sungur ile iletişim kurulamadı.", detail=str(payload))
            self.txt_otp_report.setPlainText(f"HATA: {payload}")
            return

        call_ok, msg, resp_data = payload
        if not call_ok:
            self.info("Başarısız", msg)
            self.txt_otp_report.setPlainText(f"BAŞARISIZ: {msg}")
            return

        data = resp_data or {}
        boards = data.get("boards", {})
        total = data.get("total", 0)
        successful = data.get("successful", 0)
        failed = data.get("failed", 0)

        lines = [f"{'TEST (DRY-RUN)' if dry_run else 'DAĞITIM'} RAPORU: {successful}/{total} tahta başarılı"]
        lines.append("=" * 60)
        for b_name, b_info in sorted(boards.items()):
            if b_info.get("ok"):
                user_found = b_info.get("user", "")
                h = b_info.get("hash", "")[:8]
                lines.append(f"✓ {b_name}: Başarılı (Kullanıcı: {user_found}, Hash: {h})")
            else:
                err = b_info.get("error", "Bilinmeyen hata")
                lines.append(f"✗ {b_name}: {err}")

        report_str = "\n".join(lines)
        self.txt_otp_report.setPlainText(report_str)

        if failed == 0 and total > 0:
            self.info(
                "İşlem Başarılı" if not dry_run else "Test Başarılı",
                f"Tüm tahtalar ({successful}/{total}) başarıyla tamamlandı.\n"
                f"{'Artık telefonunuzdaki OTP kodu ile tahtalara giriş yapabilirsiniz.' if not dry_run else 'Tüm tahtalar OTP dağıtımına hazır.'}"
            )
        else:
            self.info(
                "İşlem Tamamlandı (Kısmi Başarı)",
                f"{successful}/{total} tahta başarılı oldu. {failed} tahtada hata oluştu.\n"
                f"Ayrıntılar için aşağıdaki rapor alanını inceleyiniz."
            )



def run():
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    except Exception:
        pass
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    try:
        qss_path = app_asset("eta.qss")
        with open(qss_path, encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except Exception:
        pass
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
