# Gündem Botu

Türkiye'deki haber/spor sitelerinin RSS akışlarını okuyup, **15+ farklı kaynakta**
aynı anda geçen haberleri "gündem" kabul eden ve bunları kendi kendine
güncellenen bir **web sitesinde** (kaynak linkleriyle birlikte) yayınlayan
tamamen ücretsiz bir sistem.

## Nasıl çalışıyor?
- `rss_kaynaklari.py` → takip edilecek haber sitelerinin listesi
- `gundem_bot.py` → RSS'leri okur, benzer başlıkları gruplar, eşiği geçenleri
  `docs/index.html` adlı sayfaya yazar (her haberin altında kaynak linkleri var)
- `.github/workflows/gundem.yml` → GitHub'ın **ücretsiz** sunucularında botu her 30
  dakikada bir otomatik çalıştırır, sayfayı üretir ve repoya geri gönderir
- **GitHub Pages** bu `docs/index.html` dosyasını otomatik olarak canlı bir
  web sitesi olarak yayınlar — kendi linkin olur: `kullaniciadin.github.io/repo-adi`

Tasarım fikri: sayfa bir "haber ajansı teleks/wire servisi" gibi kurgulandı —
her haberin yanında kaç kaynakta geçtiğini gösteren bir "sinyal metre" var,
en çok kaynakta geçen haber en üstte.

## Kurulum (10 dakika sürer, mail/şifre gerekmiyor)

### 1) GitHub'a repo oluştur
1. github.com üzerinde ücretsiz hesap aç (yoksa)
2. Yeni bir **public repository** oluştur (adı önemli değil, örn. `gundem-botu`)
   - Public seç, çünkü GitHub Pages ücretsiz plan public repolarda sınırsız çalışır
3. Bu klasördeki tüm dosyaları (rss_kaynaklari.py, gundem_bot.py,
   requirements.txt, .github/ klasörü) o repoya yükle
   - En kolayı: GitHub sayfasında "Add file → Upload files" ile sürükle-bırak
   - `.github/workflows/gundem.yml` dosyasının klasör yapısını koruyarak
     yüklendiğinden emin ol (GitHub'a sürüklerken klasör yapısını korur)

### 2) GitHub Pages'i aç
1. Repo sayfasında **Settings → Pages**
2. "Build and deployment" altında **Source: Deploy from a branch** seç
3. Branch: **main**, klasör: **/docs** seç → **Save**
4. Bot ilk kez çalışıp `docs/index.html` dosyasını oluşturunca (bkz. adım 3),
   birkaç dakika içinde sayfan şu adreste yayında olacak:
   `https://kullaniciadin.github.io/repo-adi/`

### 3) Botu ilk kez elle çalıştır
1. Repo sayfasında **Actions** sekmesine git
2. "Gündem Botu" workflow'unu seç → sağ üstten **Run workflow** butonuna bas
3. Birkaç dakika sonra biter, `docs/index.html` otomatik olarak repoya commit'lenir
4. Sayfanı yenile (`kullaniciadin.github.io/repo-adi`) — gündem listesini görmelisin

Bundan sonra hiçbir şey yapmana gerek yok — sistem otomatik olarak her 30
dakikada bir kendi kendine çalışıp sayfayı güncelleyecek.

## Ayarları değiştirmek istersen (`gundem_bot.py` içindeki AYARLAR bölümü)
- `MIN_KAYNAK_SAYISI = 15` → bir haberin "gündem" sayılması için gereken min. kaynak sayısı
- `BENZERLIK_ESIGI = 65` → başlıklar ne kadar benzerse "aynı haber" sayılsın (0-100)
- `MAKS_GUNDEM_HABER = 10` → maile en fazla kaç haber koyulsun

## Kaynak listesini 50'ye tamamlamak
Şu an listede ~23 gerçek/doğrulanmış kaynak var. Daha fazla eklemek için
`rss_kaynaklari.py` dosyasına şu formatta yeni satırlar ekle:

```python
("Site Adı", "https://siteadi.com/rss-linki", "genel"),  # ya da "spor"
```

Yeni bir sitenin RSS linkini bulmak için genelde `siteadi.com/rss` ya da
sitenin altbilgisinde (footer) "RSS" ikonuna bakabilirsin.

⚠️ **Önemli:** Kaynak sayısı arttıkça `MIN_KAYNAK_SAYISI` eşiğini de mantıklı
şekilde güncellemen gerekir (örneğin 50 kaynağa çıkarsan eşiği 20-25 yapmak
daha doğru olabilir — çok düşük tutarsan alakasız haberler de "gündem"
sayılır, çok yüksek tutarsan hiçbir haber eşiği geçemez).

## Bilinen sınırlamalar (dürüst olmak gerekirse)
- Bazı RSS linkleri zaman içinde değişebilir/bozulabilir — script böyle bir
  kaynağı otomatik atlar, sistemi durdurmaz, ama arada bir listeyi
  kontrol etmen iyi olur.
- Başlık benzerliği kaba bir yöntemle (kelime örtüşmesi) hesaplanıyor;
  %100 hatasız "bu ve bu aynı haber" ayrımı yapmaz ama pratikte iyi çalışır.
- GitHub Actions'ın ücretsiz planı public (herkese açık) repolarda
  sınırsızdır; repo'yu **private** yaparsan ayda 2000 dakika ücretsiz
  kotan olur — 30 dakikada bir ~2 dk'lık çalıştırma için bu fazlasıyla
  yeterlidir.
