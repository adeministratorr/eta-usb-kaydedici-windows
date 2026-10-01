# ETA USB Kaydedici (Windows)

Pardus ETAP kullanılan etkileşimli tahtalarda USB bellekle oturum açmak için kullanılan **ETA USB Kaydedici'nin Windows sürümü**.

**USB anahtarınızı Windows bilgisayardan da hazırlayabilirsiniz.**

## Neden geliştirildi?

Pardus ETAP'taki orijinal **ETA USB Kaydedici** yalnızca Pardus kurulu bilgisayarlarda çalışıyor.

Bu nedenle Windows kullanan öğretmenler USB anahtarlarını kendi bilgisayarlarından hazırlayamıyordu.

Bu uygulama, aynı işlemi Windows üzerinden yapabilmek için geliştirildi. EBA hesabınıza bağlanarak USB belleğinizi hesabınızla eşleştirir ve etkileşimli tahtada kullanılabilecek bir USB anahtarına dönüştürür.

Tahta açısından oluşan sonuç Pardus sürümüyle aynıdır.

---

## Ne yapar?

- **USB'yi EBA'ya Kaydet ve Hesap Oluştur**
  USB belleğinizi EBA hesabınızla eşleştirir. USB'yi tahtaya taktığınızda parola girmeden oturum açabilirsiniz.

- **USB'yi EBA Hesabından Sil**
  USB belleğin EBA hesabınızdaki kaydını kaldırır.

- **USB Belleği Doğrula**
  USB belleğin tahtada çalışıp çalışmayacağını önceden kontrol eder. Ayrıca belleğin kime ait olduğunu gösterir.

- **USB Virüs Temizle**
  USB bellekteki kısayol virüslerini, bilinen zararlıları ve bunların bıraktığı kalıntıları temizler.

- **Bilgisayarı Temizle**
  USB belleklere yeniden bulaşmaya neden olabilecek zararlı dosyaları, çalışan süreçleri ve kalıcılık kayıtlarını kontrol edip temizler.

- **Okul Tahtalarına OTP (PIN) Tanımla (Sungur Entegrasyonu)**
  USB bellek taşımaya gerek kalmadan, telefonunuzdaki dinamik (30 saniyede bir yenilenen) 6 haneli OTP kodu ile akıllı tahtalarda oturum açmanızı sağlar. Yerel okul sunucusu (Sungur) üzerinden okuldaki tüm tahtalara tek tıkla güvenle dağıtılır.

---

## Gerekenler

- Windows 10 veya Windows 11, 64 bit
- İnternet bağlantısı
- **FAT32** veya **exFAT** biçiminde USB bellek veya USB SSD/HDD/NVMe
- EBA öğretmen hesabı

EBA'ya e-Devlet veya MEBBİS üzerinden giriş yapabilirsiniz.

> ⚠️ ISO yazdırılmış kurulum bellekleri, Ventoy kullanılan USB'ler ve NTFS biçimindeki diskler desteklenmez.
>
> Dahili sabit diskler (C: vb.) listelenmez.
>
> Salt okunur veya kilitli USB bellekler de kullanılamaz.

---

# Kullanım

## 1. USB belleği kaydetme

1. USB belleğinizi bilgisayara takın.

2. Programı açın ve **USB'yi EBA'ya Kaydet ve Hesap Oluştur** düğmesine basın.

3. Listeden USB belleğinizi seçip **Seç** düğmesine basın.

   Sürücü harfi her bilgisayarda farklı olabilir (`E:\`, `F:\` gibi). USB belleğinizi adından ve kapasitesinden kontrol ederek seçebilirsiniz.

   Bellek listede görünmüyorsa **Yenile** düğmesine basın.

4. Açılan **EBA Giriş** penceresinden EBA hesabınıza giriş yapın.

   e-Devlet dâhil EBA'nın sunduğu giriş yöntemlerini kullanabilirsiniz.

5. **USB Kaydı Oluştur** ekranında kullanıcı adınız otomatik olarak gelir.

   **Parola Üret** düğmesiyle rastgele bir parola oluşturabilir veya kendi parolanızı belirleyebilirsiniz.

   Her iki parola alanına da aynı parolayı yazın.

6. **USB'yi EBA'ya Kaydet ve Hesap Oluştur** düğmesine basın.

   Ekrana gelen bilgilendirmeyi okuyup **Tamam** diyerek işlemi onaylayın.

7. **Başarılı** mesajını gördüğünüzde USB belleğiniz kullanıma hazırdır.

> 📝 **Parolanızı bir yere not edin.**
>
> USB belleğiniz yanınızda olmadığında tahtada bu parolayla da oturum açabilirsiniz.

> 🔑 **Bir hesapta aynı anda yalnızca bir USB kayıtlı olabilir.**
>
> Yeni bir USB kaydettiğinizde daha önce kaydettiğiniz USB artık tahtada çalışmaz.
>
> Kayıt dosyasını başka bir USB belleğe kopyalamak da işe yaramaz. Her USB belleğin seri numarası farklıdır.

---

## 2. Tahtada kullanma

1. Etkileşimli tahta **giriş ekranındayken** USB belleğinizi takın.

   Oturumunuz otomatik olarak açılır.

2. İşiniz bittiğinde USB belleği çıkarın.

   Oturum otomatik olarak kapanır.

---

## 3. USB kaydını silme

1. USB belleğinizi bilgisayara takın.

2. Programda **USB'yi EBA Hesabından Sil** düğmesine basın.

3. Listeden USB belleğinizi seçin.

   USB takılı değilse **USB Seçmeden Devam Et** seçeneğini kullanabilirsiniz. Bu durumda yalnızca EBA'daki kayıt silinir, USB içindeki kayıt dosyası temizlenmez.

4. EBA hesabınıza giriş yapın.

5. Silme işlemini onaylayın.

İşlem tamamlandığında USB belleğin EBA hesabınızdaki kaydı silinir. USB seçilmişse belleğin içindeki kayıt dosyası da temizlenir.

---

## 4. USB belleği doğrulama

USB belleğinizin doğru şekilde hazırlanıp hazırlanmadığından emin olmak için **USB Belleği Doğrula** düğmesini kullanabilirsiniz.

Program şu kontrolleri yapar:

- Kayıt dosyası sağlam mı?
- Kayıt dosyası bu USB belleğe mi ait?
- Dosya başka bir USB bellekten kopyalanmış mı?
- EBA'daki USB kaydı hâlâ geçerli mi?

Kontrol tamamlandığında USB belleğin sahibini, kullanıcı adını ve yapılan kontrollerin sonuçlarını görebilirsiniz.

Tüm kontroller **✓** olarak görünüyorsa USB bellek tahtada çalışmaya hazırdır.

---

## 5. Okul tahtalarına OTP (PIN) tanımlama (Sungur Entegrasyonu)

### ❓ Bu özellik nedir ve ne işe yarar?
Akıllı tahtalarda oturum açmak için USB bellek taşımak istemiyorsanız, USB'nizi unuttuysanız veya virüs bulaşma riskinden tamamen kurtulmak istiyorsanız **Dinamik OTP (PIN)** özelliğini kullanabilirsiniz.

Bu özellik sayesinde:
* **USB Taşımaya Son:** Sadece akıllı telefonunuzu kullanarak tahtayı saniyeler içinde açabilirsiniz.
* **Sabit Şifre Yok:** Güvenliğiniz için sabit şifre kullanılmaz. Telefonunuzdaki kimlik doğrulayıcı uygulama (Google Authenticator vb.) **her 30 saniyede bir değişen tek kullanımlık 6 haneli kod** üretir.
* **Tüm Sınıflar Tek Tıkla:** Okulunuzdaki yerel **Sungur Sunucusu** sayesinde sınıfları tek tek gezmenize gerek kalmaz; anahtarınız okuldaki tüm akıllı tahtalara tek tıkla otomatik olarak tanımlanır.

---

### ⚠️ "Okul Tahtalarına OTP (PIN) Tanımla" Düğmesi Neden Pasif (Tıklanamaz)?
Program ana ekranında bu düğme **yalnızca bilgisayarınız okulun yerel ağına bağlıysa ve Sungur sunucusuna erişebiliyorsa aktifleşir**.

* **Evde veya okul dışındaysanız:** Düğme pasif kalır ve altında `○ Sungur bulunamadı (Bu özellik yalnızca okul yerel ağında kullanılabilir)` uyarısı görünür. Çünkü tahtalara erişim sağlayan Sungur sunucusu sadece okulun yerel ağında çalışır.
* **Okul ağındaysanız (Tahta ağı / Okul Wi-Fi):** Program otomatik olarak Sungur'u algılar, yeşil `● Okul ağı aktif — Sungur sunucusuna bağlandı` rozeti çıkar ve düğme tıklanabilir hale gelir.

---

### 📱 Adım Adım Kurulum ve Kullanım Rehberi

#### 1. Adım: Başlatma ve EBA Girişi
1. Bilgisayarınız okul ağına bağlıyken programı açın ve **🔑 Okul Tahtalarına OTP (PIN) Tanımla (Sungur)** düğmesine basın.
2. Açılan pencereden EBA hesabınıza (e-Devlet veya MEBBİS ile) giriş yapın.
3. EBA'daki adınız, kullanıcı adınız ve EBA ID'niz otomatik olarak ekrana gelecektir.

#### 2. Adım: Telefonunuza Tanımlama (QR Kod)
1. Telefonunuza ücretsiz bir TOTP uygulaması yükleyin (Örn: **Google Authenticator**, **FreeOTP**, **Microsoft Authenticator**).
2. Uygulamayı açıp **+ (Hesap Ekle)** düğmesine basın ve **QR Kodunu Tara** seçeneğini seçin.
3. Bilgisayar ekranındaki karekodu kameranızla okutun.
4. Artık telefonunuzda okul tahtaları için 30 saniyede bir yenilenen 6 haneli kod üretilmeye başlayacaktır!

#### 3. Adım: Tahtalara Dağıtma
1. Ekrandaki **Sungur Sunucu** alanında okul yöneticinizin verdiği sunucu adresi (varsayılan: `http://etap-sungur.local:8080`) ve **Yönetici Parolası (Token)** yer alır.
2. **🔌 Bağlantıyı Test Et** düğmesine basarak Sungur'un kaç tahtayla iletişimde olduğunu kontrol edin.
3. İsterseniz **🔍 Tahtaları Test Et (Dry-Run)** ile tahtaların durumunu önceden görün.
4. **🚀 Okuldaki Tüm Tahtalara Dağıt** düğmesine basın.
5. Sungur saniyeler içinde okuldaki tüm tahtaların `/etc/otp-secrets.json` kütüğüne anahtarınızı güvenle işler ve işlem sonucunu tahta tahta ekranda raporlar.

#### 4. Adım: Tahtada Oturum Açma
* Herhangi bir sınıftaki akıllı tahtanın giriş ekranına gidin.
* Kullanıcı adı kısmına adınızı (`adem.yuce` vb.) yazın.
* Şifre alanına telefonunuzdaki **Google Authenticator uygulamasında o an görünen 6 haneli kodu** yazıp Enter'a basın.
* Oturumunuz anında açılır!

---

### 💡 Sıkça Sorulan Sorular (SSS)

**S: İnternet kesilirse tahtada OTP ile oturum açabilir miyim?**  
**C:** Evet! TOTP (RFC 6238) matematiksel bir saat algoritmasıdır. Tahtanın ve telefonunuzun saati doğru olduğu sürece internet bağlantısına ihtiyaç duymadan çalışır.

**S: Tahtadaki masaüstüm, ev dizinim veya dosyalarım silinir mi?**  
**C:** Kesinlikle hayır! Sistem EBA ID'niz üzerinden tahtadaki mevcut hesabınızı bulur ve korur. Yalnızca kilit dosyasına yetkiniz eklenir.

**S: Eski USB belleğim çalışmaya devam eder mi?**  
**C:** Evet! USB anahtarınız ve OTP yöntemini aynı anda kullanabilirsiniz. İster USB takın, ister telefonunuzdaki kodu yazın.

**S: Başka bir öğretmenin PIN yetkisi silinir mi?**  
**C:** Hayır. Sungur sunucusu atomik birleştirme (merge) ve SHA-256 mühürleme tekniği kullanır. Yeni eklenen öğretmenler mevcut öğretmen listesine eklenir, kimsenin anahtarı ezilmez.

**S: Telefonumu değiştirirsem ne yapmalıyım?**  
**C:** Yeni telefonunuzla bu programa tekrar girip EBA doğrulaması yapın, **Yeni Anahtar** düğmesine basıp yeni QR kodu okutun ve tekrar **Tüm Tahtalara Dağıt** deyin. Eski kodunuz geçersiz olur, yenisi aktifleşir.

---

# Virüs ve zararlı yazılım temizleme

USB belleklerde görülen kısayol virüsleri ve benzeri zararlı yazılımlar dosya ve klasörlerinizi gizleyebilir, sahte kısayollar oluşturabilir veya dosyalarınızı başka klasörlere taşıyabilir.

`Musallat.exe`, `Özel Dosyalar.exe` ve sahte `.lnk` dosyaları bu tür zararlılara örnektir.

Bu zararlılar ETA USB Kaydedici tarafından oluşturulan kayıt dosyasını da başka bir klasöre taşıyabilir. Kayıt dosyası USB belleğin kök dizininde bulunmazsa bellek tahtada çalışmaz.

Programda bunun için iki ayrı temizleme aracı bulunur.

## USB Virüs Temizle

**USB Virüs Temizle**, USB bellekte sık karşılaşılan zararlıların bıraktığı dosya ve değişiklikleri kontrol eder.

Temizlik sırasında klasik olarak kullanılan:

```bat
del *.lnk
```

ve

```bat
attrib -h -r -s /s /d
```

işlemleri uygulanır ve ek kontroller yapılır.

Program:

- USB belleğin kök dizinindeki tüm kısayolları (`.lnk`),
- `autorun.inf` dosyasını,
- `Musallat.exe` gibi bilinen zararlıları,
- kök dizindeki şüpheli çalıştırılabilir uzantıları (`.scr`, `.pif`, `.com`, `.bat`, `.vbs`, `.js` ile `.ini`, `.bak`, `.bin`)

kontrol eder.

Silinecek dosyalar kullanıcıya gösterilir ve işlem **onay alındıktan sonra** gerçekleştirilir.

`thumbs.db`, `.DS_Store` ve macOS artıkları (`._*`) korunur, taramada yok sayılır. Kök dizindeki `desktop.ini` dahil `.ini` uzantılı dosyalar şüpheli sayılır ve onayınızla silinir.

Zararlı tarafından gizlenen dosya ve klasörlerin gizli, salt okunur ve sistem özellikleri kaldırılarak yeniden görünür hâle getirilir. Bu işlem alt klasörleri de kapsar.

Dosyalar isimsiz bir klasöre (Alt+0160 boşluk karakteri vb.) veya sürücü etiketiyle aynı isimli bir klasöre (örn. KINGSTON) taşınmışsa temizleme bitince bu klasörün içindekiler USB belleğin kök dizinine geri taşınır. Boş kalan zulalama klasörü silinir.

Taşınmış `.credentials` dosyası da yeniden USB belleğin kök dizinine getirilir.

Programın tanımadığı `.exe` dosyaları otomatik olarak silinmez; yalnızca listelenir.

---

## Bilgisayarı Temizle

USB belleği temizlemek tek başına yeterli olmayabilir.

Zararlı yazılım bilgisayarda çalışmaya devam ediyorsa temizlenen USB bellek bilgisayara yeniden takıldığında tekrar enfekte olabilir.

**Bilgisayarı Temizle** seçeneği bu nedenle zararlının bilgisayarda kullandığı dosyaları, çalışan süreçleri ve kalıcılık noktalarını kontrol eder.

Program şu alanları denetler:

- `%TEMP%` içindeki `.vbs` dosyaları
- `tmp*.tmp.exe` biçimindeki dosyalar
- `Musallat.exe`
- Başlangıç klasöründeki `.vbs` kalıntıları
- HKCU Run kayıtları
- Rastgele adlarla oluşturulmuş başlangıç girdileri
- `MusaLLat.exe` kayıtları
- `wscript` çalıştıran şüpheli girdiler
- Görev Yöneticisi ve Kayıt Defteri için oluşturulmuş kısıtlamalar
- Çalışan zararlı süreçler

Şüpheli komut satırıyla çalışan `wscript` süreçleri de kontrol edilir.

Bazı zararlı yazılımlar kendilerini sistem dosyası gibi göstermek için `wuauclt`, `rundll32` veya `TrustedInstaller` gibi adlar kullanabilir.

Bu tür durumlarda yalnızca işlem adına bakılmaz; dosyanın çalıştığı gerçek konum da kontrol edilir.

Zararlı bir süreç tespit edildiğinde önce çalışan süreç sonlandırılır, ardından ilgili dosya ve kayıtlar silinir.

Makine geneli kalıcılık noktaları (HKLM Run, tüm kullanıcıların Başlangıç klasörü) de denetlenir. Bunların silinmesi yönetici yetkisi gerektirir.

Temizlik tamamlandıktan sonra bilgisayarınızı yeniden başlatın.

Ardından Windows Defender ile **Tam Tarama** yapmanız önerilir.

USB belleği temizledikten sonra **USB Belleği Doğrula** ile tekrar kontrol edebilirsiniz.

Kayıt sırasında oluşturulan `.credentials` dosyası ayrıca korumaya alınır. Bu koruma etkileşimli tahtanın dosyayı okumasını engellemez.

---

# Çalışmazsa ne yapmalı?

| Gördüğünüz mesaj | Anlamı ve çözümü |
|---|---|
| USB bulunamadı | USB bellek takılı değil. Belleği takıp **Yenile** düğmesine basın. |
| Bağlı değil veya formatlanmamış | Bellek ham veya desteklenmeyen biçimde. **FAT32** olarak biçimlendirin. |
| Seri numarası okunamadı | USB belleği başka bir porta takıp yeniden deneyin. Sorun devam ederse başka bir bellek kullanın. |
| ISO yazdırılmış medya desteklenmez | Kurulum USB'si kullanılamaz. Standart bir USB bellek kullanın. |
| Salt okunur | Bellekte fiziksel kilit varsa açın veya belleği FAT32 olarak biçimlendirin. |
| EBA'ya ulaşılamadı | İnternet bağlantısını, bilgisayarın tarih ve saatini ve güvenlik duvarını kontrol edin. |
| EBA oturumu geçersiz | Oturum süresi dolmuş. EBA penceresini kapatıp yeniden giriş yapın. |
| USB parolası eşleşmedi | Parola adımını yeniden uygulayın. Sorun devam ederse EBA'ya MEBBİS ile giriş yapıp yeni USB şifresi alın. |
| Silinecek kayıt yok | Bu TCKN'ye ait USB kaydı EBA'da yok. Normal durumdur, işlem yapmanıza gerek yok. |
| Gönderilen bilgiler reddedildi (EBA.017) | Bilgileri kontrol edip yeniden deneyin. Aynı USB başka bir hesaba kayıtlıysa önce o kayıt silinmelidir. |

---

# Güvenlik

Parolanız USB belleğe açık olarak yazılmaz. Parolanın **karma (hash) değeri** saklanır.

Program EBA ile doğrudan iletişim kurar. Bilgileriniz başka bir sunucuya gönderilmez.

USB belleğinizi kaybederseniz programı kullanarak EBA hesabınızdaki USB kaydını silebilirsiniz. Kayıt silindikten sonra USB belleği bulan kişi bu bellekle tahtada oturum açamaz.

Program açılışta Windows'tan **yönetici onayı (UAC)** ister.

Bunun nedeni bilgisayar genelindeki bazı zararlı kalıcılık noktalarının yalnızca yönetici yetkisiyle temizlenebilmesidir.

Örneğin:

- HKLM Run kayıtları
- Tüm kullanıcıların Başlangıç klasörü

yönetici yetkisi gerektirir.

Yönetici onayı vermezseniz program yine açılır ancak bu alanlar yalnızca okunur olarak listelenir.

---

# Windows güvenliği: SmartScreen ve Defender

Programı ilk kez çalıştırdığınızda Windows **Bilinmeyen yayımcı** uyarısı gösterebilir.

Bu durumda:

**Ek bilgi → Yine de çalıştır**

seçeneğini kullanabilirsiniz.

Bu, dijital olarak imzalanmamış uygulamalarda görülebilen standart SmartScreen uyarısıdır.

Programın zararlı temizleme özellikleri dosya silme, çalışan süreçleri sonlandırma ve Kayıt Defteri üzerinde değişiklik yapma gibi işlemler gerçekleştirir.

Antivirüs yazılımları bu tür davranışları zaman zaman şüpheli olarak değerlendirebilir.

Uygulamada bu nedenle şu önlemler uygulanır:

- Derleme tek dosya (`onefile`) olarak hazırlanır (Qt6 DLL'leri CFG korumalı olduğundan UPX etkisizdir, bu yüzden UPX kullanılmaz).
- EXE dosyasına ürün, sürüm ve yayımcı bilgileri eklenir (`version_info.txt`).
- Dosya silme ve kaldırma işlemleri kullanıcı onayıyla yapılır.
- Program kendiliğinden dosya silmez.
- Kaynak kodu açıktır.
- İstenirse program doğrudan kaynak kodundan çalıştırılabilir:

```bat
python src\main.py
```

Yanlış pozitif tespit durumunda dosya Microsoft'a inceleme için gönderilebilir:

<https://www.microsoft.com/wdsi/filesubmission>

Kalıcı çözüm kod imzalama sertifikası kullanmaktır. İleride sertifika edinildiğinde Windows derlemesi dijital olarak imzalanabilir.

---

# Geliştiriciler için

Kaynak: Pardus `eta-usb-register 2.0.6` uygulamasının **GPL-3.0+ lisanslı Windows uyarlaması**.

Tahtadaki giriş denetimi (`eta-usb-login`) aynı şekilde uygulanmıştır.

Kaynak koddan çalıştırmak için:

```bat
pip install -r requirements.txt
python src\main.py
```

---

# Windows'ta EXE oluşturma

Gerekenler:

- Windows 10 veya Windows 11, 64 bit
- [Python 3.11](https://www.python.org/downloads/)

Python kurulumu sırasında **Add python.exe to PATH** seçeneğini işaretleyin.

Ardından:

```bat
git clone https://github.com/adeministratorr/eta-usb-kaydedici-windows.git
cd eta-usb-kaydedici-windows

pip install -r requirements.txt
pip install pyinstaller

python -m PyInstaller --noconfirm --onefile --windowed --name "ETA-USB-Kaydedici" --version-file version_info.txt --icon assets/logo.ico --add-data "assets;assets" --collect-all PySide6 src/main.py
```

> **Önemli Güvenlik Notu (Sungur & Yerel Ağ):**
> Sungur filo sunucusu ile iletişimde OTP sırları ve yönetici erişim token'ı aktarılmaktadır. Bu sebeple açık/şifresiz veya güvensiz ortak Wi-Fi ağlarında kullanılmamalı, üretim ortamında mutlaka **HTTPS (TLS)** kullanılmalıdır. Token'lar yerel Windows kayıt defterinde **DPAPI** ile şifrelenerek korunur.

> `pyinstaller` yerine `python -m PyInstaller` kullanabilirsiniz.
>
> Aynı işlemi yapar ancak `PATH` kaynaklı sorunlardan etkilenmez.

Derleme tamamlandığında dosya şu konumda oluşur:

```text
dist\ETA-USB-Kaydedici.exe
```

Uygulama tek dosya olarak çalışır. Kurulum gerekmez.

> Not: CI'da kullanılan tam derleme komutu gereksiz Qt modüllerinin çıkarılmasını da içerir (`--collect-all PySide6` kullanılmaz; UPX kullanılmaz çünkü Qt6 CFG'li DLL'lerde etkisizdir). Güncel tam komut için `.github/workflows/build-windows.yml` dosyasına bakın.

---

## "pyinstaller bulunamadı / not recognized" hatası

Önce PyInstaller'ın kurulu olup olmadığını kontrol edin:

```bat
pip show pyinstaller
```

Kurulu değilse:

```bat
pip install pyinstaller
```

PyInstaller kurulu olduğu hâlde komut bulunamıyorsa:

```bat
python -m PyInstaller --version
```

komutunu kullanın.

Bilgisayarda birden fazla Python kurulumu varsa `pip` ve `python` farklı kurulumları kullanıyor olabilir.

Bu durumda:

```bat
python -m pip install pyinstaller
python -m PyInstaller --version
```

komutlarını kullanın.

Sanal ortam (`venv`) kullanıyorsanız önce ortamı etkinleştirin, ardından PyInstaller'ı kurun.

---

## macOS notu

macOS'ta `python` yerine genellikle `python3` komutu kullanılır:

```bash
python3 -m pip install pyinstaller
python3 -m PyInstaller --version
```

Windows için kullanılacak son EXE dosyası (`--version-file`, `pywin32`) yalnızca Windows üzerinde üretilebilir.

Mac üzerinde derleme yaparsanız Windows EXE'si değil, macOS için çalıştırılabilir bir uygulama oluşur.

---

## Sorun yaşarsanız

SmartScreen uyarısı çıkarsa:

**Ek bilgi → Yine de çalıştır**

seçeneğini kullanın.

**EBA Giriş** penceresi boş geliyorsa:

```bat
pip install PySide6-Addons
```

komutunu çalıştırın.

Sorun devam ederse:

```bat
pip install --force-reinstall PySide6
```

komutuyla PySide6'yı yeniden kurabilirsiniz.

Bu durum WebEngine bileşeninin eksik olmasından kaynaklanabilir.

---

# Lisans

**GPL-3.0+**

Pardus `eta-usb-register` ile aynı lisans kullanılır.
