"""Qt ana pencere. Akis birebir orijinal eta-usb-register 2.0.6 ile ayni:

start -> usb_select -> EBA web -> register (veya silmede dogrudan onay) -> start.

Sayfa isimleri, buton metinleri ve dialog cumleleri orijinal
MainWindow.glade / MainWindow.py'dan alindi. Windows'a ozel ekler
(Flash Dogrula, virus temizligi) ana ekranda ayri bolumde durur.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QSizePolicy, QStackedWidget, QTextEdit, QVBoxLayout, QWidget,
)

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False

import credentials_manager as CredentialsManager
import eba_client
import eba_errors
import flash_verify
import usb_manager_win
import virus_cleaner


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
        self.view = QWebEngineView(self)
        self.view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view.load(QUrl(eba_errors.EBA_URL))
        self.view.urlChanged.connect(self._on_url)
        layout.addWidget(self.view, 1)

    def _on_url(self, url):
        s = url.toString()
        if "api" in s and "token=" in s:
            token = s.split("token=")[1].strip()
            self.token = token
            self.login_done.emit(token, s)
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

        central = QWidget(self)
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)

        # Ust bar: Hakkinda (orijinaldeki help-about karsiligi)
        top = QHBoxLayout()
        top.addStretch(1)
        self.btn_about = QPushButton("Hakkında")
        self.btn_about.clicked.connect(self.show_about)
        top.addWidget(self.btn_about)
        outer.addLayout(top)

        self.stack = QStackedWidget(self)
        outer.addWidget(self.stack, 1)

        self.page_start = self._build_start_page()
        self.page_usb = self._build_usb_page()
        self.page_register = self._build_register_page()
        self.page_spinner = self._build_spinner_page()
        self.stack.addWidget(self.page_start)      # 0: start
        self.stack.addWidget(self.page_usb)        # 1: usb_select
        self.stack.addWidget(self.page_register)   # 2: register
        self.stack.addWidget(self.page_spinner)    # 3: spinner

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
        self.btn_delete.clicked.connect(self.on_btn_delete_clicked)
        self.btn_register = QPushButton("USB'yi EBA'ya Kaydet ve Hesap Oluştur")
        self.btn_register.clicked.connect(self.on_btn_register_clicked)
        row.addWidget(self.btn_delete)
        row.addWidget(self.btn_register)
        lay.addLayout(row)
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
        lay.addStretch(1)
        return pg

    def _sep(self):
        from PySide6.QtWidgets import QFrame
        f = QFrame()
        f.setFrameShape(QFrame.HLine)
        return f

    # --- yardimcilar ---
    def log(self, t):
        self.out.append(t)

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

    def show_start(self):
        self.stack.setCurrentIndex(0)

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

    # --- usb_select sayfasi ---
    def refresh_usb(self):
        self.devices = usb_manager_win.list_usb_devices_win()
        self.cmb.blockSignals(True)
        self.cmb.clear()
        for d in self.devices:
            self.cmb.addItem(f"{d.get('label')} — {d.get('mountpoint')} [{d.get('serial')}] ({d.get('fstype')})")
        self.cmb.blockSignals(False)
        if self.devices:
            self.cmb.setCurrentIndex(0)
            self.on_cmb_changed(0)
        else:
            self.lbl_usb_warn.setText("USB bulunamadı. USB belleği takıp Yenile'ye basın.")
            self.btn_select_usb.setEnabled(False)

    def on_cmb_changed(self, i):
        dev = self.devices[i] if 0 <= i < len(self.devices) else None
        if not dev:
            self.lbl_usb_warn.setText("USB bulunamadı. USB belleği takıp Yenile'ye basın.")
            self.btn_select_usb.setEnabled(False)
            return
        # EBA girisine sokmadan bastan ele: seri/format/yazilabilirlik burada belli olsun
        ok, title, msg = usb_manager_win.preflight(dev)
        if not ok:
            self.lbl_usb_warn.setText(f"{title}: {msg}")
            self.btn_select_usb.setEnabled(False)
        else:
            self.lbl_usb_warn.setText("")
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
        self.stack.setCurrentIndex(3)  # spinner
        QApplication.processEvents()
        ok, data = eba_client.get_teacher_info(info_url)
        if not ok:
            self.info(data["title"], data["message"], data.get("action", ""), data.get("detail", ""))
            self.token = ""
            self.stack.setCurrentIndex(0)
            return
        self.teacher = data
        if self.mode == "delete":
            if self.ask("Emin misiniz?",
                        "EBA'daki Akıllı Tahta USB ile giriş kaydınız silinecek."):
                self.delete_usb_record()
            self.token = ""
            self.show_start()
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
        if self.register_usb():
            self.token = ""
            self.show_start()

    def register_usb(self):
        p1 = self.ed_pass.text()
        if not p1:
            self.info("Başarısız!", "Parola girmeyi unutmayınız.")
            return False
        if not self.teacher or not self.teacher.get("username"):
            self.info("Başarısız!",
                      "Kullanıcı Adı bilgisi eksik. EBA'ya giriş yaptığınızdan emin olunuz.")
            return False
        dev = self.usb or {}
        ok, title, msg = usb_manager_win.preflight(dev)
        if not ok:
            self.info(title, msg)
            return False
        self.log("Şifre EBA'ya gönderiliyor...")
        QApplication.processEvents()
        ok, err = eba_client.reset_password(self.token, p1, self.teacher["tckn"])
        if not ok:
            self.info(err["title"], err["message"], err.get("action", ""), err.get("detail", ""))
            return False
        self.log("USB kaydediliyor...")
        QApplication.processEvents()
        ok, res = eba_client.register_usb(self.teacher["tckn"], p1, self.teacher["eba_id"],
                                          dev["serial"], self.teacher["username"])
        if not ok:
            self.info(res["title"], res["message"], res.get("action", ""), res.get("detail", ""))
            return False
        from passlib.hash import bcrypt
        content = {"eba_id": self.teacher["eba_id"],
                   "username": self.teacher["username"],
                   "usb_serial": dev["serial"],
                   "password": bcrypt.hash(p1),
                   "name": self.teacher["name"]}
        path = os.path.join(dev["mountpoint"], ".credentials")
        wok, werr = CredentialsManager.save_credentials_file(path, content)
        if wok:
            try:
                virus_cleaner.protect_credentials(path)
            except Exception:
                pass
            self.info("Başarılı",
                      "EBA Hesabınızdaki USB Kaydı yenilendi ve yeni USB'nize kaydedildi.")
            self.log(f"Yazıldı: {path}")
            return True
        home = os.path.expanduser("~")
        fb = os.path.join(home, "1.credentials")
        wok2, _ = CredentialsManager.save_credentials_file(fb, content)
        if wok2:
            self.info("Dikkat!",
                      "Hesap bilgileri, Ev dizinine '1.credentials' ismiyle kaydedildi.\n"
                      "Lütfen dosyayı USB'nize kopyalayın ve başındaki 1'i silin.",
                      detail=str(werr))
            return True
        self.info("Başarısız!",
                  f"Hesap bilgileri, USB'ye veya Ev dizinine('{fb}') kaydedilemedi.Hata:\n\n{werr}")
        return False

    # --- sil ---
    def delete_usb_record(self):
        if not self.teacher or not self.teacher.get("tckn"):
            self.info("TC Kimlik No bulunamadı", "EBA'ya giriş yaptığınızdan emin olun.")
            return False
        ok, res = eba_client.delete_usb(self.teacher["tckn"])
        if ok:
            try:
                if self.usb and self.usb.get("mountpoint"):
                    fp = os.path.join(self.usb["mountpoint"], ".credentials")
                    if os.path.exists(fp):
                        try:
                            virus_cleaner.clear_attrs(fp)
                        except Exception:
                            pass
                        os.remove(fp)
            except Exception as e:
                self.log(f".credentials silinemedi: {e}")
            self.info("Başarılı", "EBA Hesabınızdaki USB Kaydı silindi.")
            return True
        if res.get("not_found"):
            self.info("Başarısız!", "USB daha önce eklenmemiş.")
        else:
            self.info(res["title"], res["message"], res.get("action", ""), res.get("detail", ""))
        return False

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
        res = flash_verify.verify_flash(dev, check_server=True)
        o = res["owner"]
        lines = []
        if o:
            lines.append(f"Sahip: {o['name']} ({o['username']})")
            lines.append(f"Seri: {o['usb_serial']} | EBA ID: {o['eba_id_masked']}")
        for name, good, msg in res["checks"]:
            lines.append(f"{'✓' if good else '✗'} {name}: {msg}")
        if res["ok"]:
            lines.append("Sonuç: Bu flash tahtada çalışır.")
        else:
            lines.append("Sonuç: Bu flash TAHTADA ÇALIŞMAZ — yukarıdaki ✗ satırına bakın.")
        lines.append("Not: USB'yi tahtada giriş ekranındayken takın.")
        self.out.setPlainText("\n".join(lines))

    def do_clean_flash(self):
        dev = self.pick_tool_device()
        if not dev:
            return
        mp = dev.get("mountpoint") or ""
        scan = virus_cleaner.scan_flash(mp, volume_label=dev.get("label") or "")
        if scan["error"]:
            self.info("USB oluşturulamaz", scan["error"])
            return
        n_bad = (len(scan["bad_exes"]) + len(scan["shortcut_hits"])
                 + len(scan["orphan_lnks"]) + (1 if scan["autorun"] else 0))
        detail = []
        if scan["autorun"]:
            detail.append("• autorun.inf")
        detail += [f"• {b}" for b in scan["bad_exes"]]
        detail += [f"• {h['lnk']} (→ {h['folder']} klasörünün sahte kısayolu)" for h in scan["shortcut_hits"]]
        detail += [f"• {l} (sahipsiz kısayol, silinecek)" for l in scan["orphan_lnks"]]
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
        rep = virus_cleaner.clean_flash(mp, volume_label=dev.get("label") or "")
        lines = [f"Silindi: {', '.join(rep['removed'])}" if rep["removed"] else "Silinen: yok"]
        if rep["unhidden"]:
            lines.append(f"Geri açıldı: {', '.join(rep['unhidden'])}")
        if rep["restored_items"]:
            lines.append("Köke iade edildi:")
            lines += [f"  • {m}" for m in rep["restored_items"]]
        if rep["restored"]:
            lines.append(rep["restored"])
        if rep["kept"]:
            lines.append(f"Ellemedim (elle bakın): {', '.join(rep['kept'])}")
        if rep["errors"]:
            lines.append("Hatalar: " + "; ".join(rep["errors"]))
        lines.append("Sonraki adım: USB Belleği Doğrula'ya basıp sahibini kontrol edin.")
        self.out.setPlainText("\n".join(lines))

    def do_clean_pc(self):
        scan = virus_cleaner.scan_pc()
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
        if not self.ask("Bunlar kaldırılsın mı?", "Şüpheli kayıtlar:\n" + "\n".join(items)):
            return
        rep = virus_cleaner.clean_pc(scan)
        lines = [f"Kaldırıldı: {', '.join(rep['removed'])}" if rep["removed"] else "Kaldırılan: yok"]
        if rep["errors"]:
            lines.append("Hatalar: " + "; ".join(rep["errors"]))
        lines.append("Önemli: temizlikten sonra bilgisayarı yeniden başlatın.")
        self.out.setPlainText("\n".join(lines))


def run():
    app = QApplication(sys.argv)
    app.setWindowIcon(app_icon())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
