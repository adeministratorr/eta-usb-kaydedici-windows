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

python -m PyInstaller --noconfirm --onefile --windowed --uac-admin --name "ETA-USB-Kaydedici" --version-file version_info.txt --icon assets/logo.ico --add-data "assets;assets" --collect-all PySide6 src/main.py
```

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

Windows için kullanılacak son EXE dosyası (`--uac-admin`, `--version-file`, `pywin32`) yalnızca Windows üzerinde üretilebilir.

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
