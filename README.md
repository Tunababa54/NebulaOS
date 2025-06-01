NebulaOS: Kozmik Bir Masaüstü Deneyimi
🌌 Proje Hakkında
NebulaOS, Python ve Tkinter kullanılarak geliştirilmiş, terminal tabanlı bir işletim sistemi simülasyonundan masaüstü benzeri bir deneyime evrilen deneysel bir projedir. Bu proje, temel işletim sistemi işlevlerini (dosya yönetimi, uygulama çalıştırma, kullanıcı yönetimi) bir GUI (Grafik Kullanıcı Arayüzü) ortamında simüle etmeyi amaçlamaktadır.

NebulaOS, hem geleneksel terminal komutlarını destekler hem de masaüstü simgeleri ve pencereler aracılığıyla etkileşimli bir kullanıcı deneyimi sunar. Kullanıcılar, dosya gezgini, hesap makinesi ve metin düzenleyici gibi basit uygulamaları çalıştırabilir, sistem durumunu görüntüleyebilir ve hatta simüle edilmiş bir SMS saldırı aracı (nebsmash) gibi pentest araçlarını deneyimleyebilirler (yalnızca eğitim ve yasal test amaçlıdır, izinsiz kullanımı yasa dışıdır).

✨ Özellikler
Masaüstü Ortamı: Özelleştirilebilir arka plan ve uygulama kısayolları.

Pencere Yönetimi: Uygulamalar ayrı pencerelerde açılır (şimdilik temel düzeyde).

Terminal Uygulaması: Tam işlevli, komut geçmişi ve çıktı yönlendirmesi olan bir terminal penceresi.

Dosya Gezgini: Sanal dosya sistemi üzerinde gezinme, dosya/dizin listeleme.

Hesap Makinesi Uygulaması: Temel aritmetik işlemler için GUI tabanlı bir hesap makinesi.

Metin Düzenleyici Uygulaması: Dosyaları açma, düzenleme ve kaydetme yeteneğine sahip basit bir metin düzenleyici.

Kullanıcı Yönetimi: root yetkisiyle kullanıcı oluşturma, silme ve parola değiştirme.

Sistem Komutları: neblist, nebjump, nebcreate, nebkill, nebsay, nebtime, nebclear, nebspawn, nebwho, nebperm, nebdelete, nebcopy, nebmove, nebhelp, neblog, nebconfig, nebuser, nebpass, nebsmash, nebview, nebdir, nebstatus, nebcom, nebinstall, nebreport, nebscan, nebexec, nebversion.

Temalar: dark_nebula ve cosmic_dawn gibi özelleştirilebilir renk temaları.

Simüle Edilmiş SMS Saldırı Aracı (nebsmash): Yalnızca eğitim ve yasal test amaçlıdır. İzinsiz kullanımı yasa dışıdır ve ciddi yasal sonuçları olabilir.

🚀 Kurulum
NebulaOS'u yerel makinenizde çalıştırmak için aşağıdaki adımları izleyin.

Önkoşullar
Python 3.x

tkinter (genellikle Python ile birlikte gelir)

requests kütüphanesi (SMS gönderme işlevi için)

pygame ve opencv-python (başlangıç videosu için isteğe bağlı)

pip install requests
pip install pygame opencv-python # İsteğe bağlı, video oynatma için

Kurulum Adımları
Bu depoyu klonlayın:

git clone https://github.com/KullaniciAdiniz/NebulaOS.git
cd NebulaOS

(KullaniciAdiniz kısmını kendi GitHub kullanıcı adınızla değiştirmeyi unutmayın.)

nebula.py dosyasını çalıştırın:

python nebula.py

🎮 Kullanım
Uygulamayı başlattığınızda, NebulaOS'un açılış ekranı ve ardından bir kurulum süreci (ilk çalıştırmada) veya doğrudan oturum açma ekranı ile karşılaşacaksınız.

İlk Kurulum
İlk kez çalıştırdığınızda, NebulaOS size dil, klavye düzeni, ülke ve tema gibi temel ayarları soracaktır. Bu adımları tamamladıktan sonra oturum açma ekranına yönlendirileceksiniz.

Oturum Açma
Varsayılan kullanıcı adları ve parolalar:

Kullanıcı Adı: root / Parola: rootpass

Kullanıcı Adı: gezgin / Parola: gezginpass

Oturum açtıktan sonra, masaüstü ortamı yüklenecektir. Masaüstünde "Terminal", "Dosyalar", "Hesap Makinesi" ve "Metin Düzenleyici" gibi simgeler bulacaksınız. Bu simgelere tıklayarak ilgili uygulamaları başlatabilirsiniz.

Terminal Kullanımı
"Terminal" simgesine tıklayarak terminal penceresini açın. Burada eski terminal komutlarını kullanmaya devam edebilirsiniz:

neblist: Mevcut dizindeki dosya ve klasörleri listeler.

nebjump <dizin_adı>: Belirtilen dizine geçer. .. ile bir üst dizine gidebilirsiniz.

nebcreate <dosya_adı> [içerik]: Yeni bir dosya oluşturur.

nebsay <mesaj>: Ekrana mesaj yazar.

nebhelp [komut_adı]: Komutlar hakkında yardım sağlar.

nebsmash <telefon_numarası> [mail_adresi] [adet]: UYARI: Bu araç sadece eğitim ve yasal test amaçlıdır. İzinsiz kullanımı yasa dışıdır ve ciddi yasal sonuçları olabilir.

Uygulama Kullanımı
Dosyalar: Temel dosya gezgini işlevselliği sunar.

Hesap Makinesi: Basit aritmetik işlemler yapar.

Metin Düzenleyici: Dosyaları açıp düzenlemenizi sağlar.

🤝 Katkıda Bulunma
NebulaOS açık kaynaklı bir projedir ve katkılarınızı memnuniyetle karşılarız! Eğer projeye katkıda bulunmak isterseniz, lütfen aşağıdaki adımları izleyin:

Bu depoyu (repository) forklayın.

Yeni bir dal (branch) oluşturun: git checkout -b ozellik/yeni-ozellik

Değişikliklerinizi yapın ve commit edin: git commit -m "feat: Yeni özellik eklendi"

Değişikliklerinizi orijinal depoya (upstream) push edin: git push origin ozellik/yeni-ozellik

Bir Pull Request (Çekme İsteği) oluşturun.

Lütfen kodlama standartlarına uymaya özen gösterin ve her yeni özellik veya düzeltme için ayrı bir dal kullanın.

📄 Lisans
Bu proje MIT Lisansı altında lisanslanmıştır. Daha fazla bilgi için LICENSE dosyasına bakın.
