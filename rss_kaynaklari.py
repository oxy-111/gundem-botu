# -*- coding: utf-8 -*-
"""
Takip edilecek RSS kaynakları.
Format: ("Kaynak Adı", "RSS URL", "kategori")  kategori: "genel" | "spor"

NOT: Bazı siteler zaman zaman RSS adreslerini değiştirebilir ya da geçici
olarak erişilemez olabilir. Script, çalışmayan bir kaynağı otomatik olarak
atlayıp diğerlerine devam edecek şekilde yazıldı (bkz. gundem_bot.py).
Zamanla listeye yeni kaynaklar ekleyebilir, bozulanları çıkarabilirsin.
"""

KAYNAKLAR = [
    # ---- Genel haber / siyaset ----
    ("Hürriyet", "https://www.hurriyet.com.tr/rss/anasayfa", "genel"),
    ("Milliyet - Gündem", "https://www.milliyet.com.tr/rss/rssNew/gundemRss.xml", "genel"),
    ("Milliyet - Siyaset", "https://www.milliyet.com.tr/rss/rssNew/siyasetRss.xml", "genel"),
    ("Sabah", "https://www.sabah.com.tr/rss/anasayfa.xml", "genel"),
    ("Sözcü", "https://www.sozcu.com.tr/feeds-son-dakika", "genel"),
    ("Cumhuriyet", "https://www.cumhuriyet.com.tr/rss/1.xml", "genel"),
    ("Haberler.com", "https://rss.haberler.com/rss.asp", "genel"),
    ("Star Gazete", "https://www.stargazete.com/rss/rss.asp", "genel"),
    ("Takvim", "https://www.takvim.com.tr/rss/anasayfa.xml", "genel"),
    ("Yeni Şafak", "https://www.yenisafak.com/rss?xml=tumhaberler", "genel"),
    ("Yeni Çağ", "https://www.yenicaggazetesi.com.tr/rss", "genel"),
    ("Türkiye Gazetesi", "https://www.turkiyegazetesi.com.tr/rss/rss.xml", "genel"),
    ("Habertürk", "https://www.haberturk.com/rss", "genel"),
    ("NTV", "https://www.ntv.com.tr/gundem.rss", "genel"),
    ("10Haber", "https://10haber.net/feed/", "genel"),

    # ---- Spor / futbol ----
    ("Sabah Spor", "https://www.sabah.com.tr/rss/spor.xml", "spor"),
    ("Sözcü Futbol", "https://www.sozcu.com.tr/feeds-rss-category-futbol", "spor"),
    ("Sözcü Spor", "https://www.sozcu.com.tr/feeds-rss-category-spor", "spor"),
    ("Sözcü Dünyadan Futbol", "https://www.sozcu.com.tr/feeds-rss-category-dunyadan-spor", "spor"),
    ("NTV Spor", "https://www.ntvspor.net/rss", "spor"),
    ("Fotomaç", "https://www.fotomac.com.tr/rss/anasayfa.xml", "spor"),
    ("Fanatik", "https://www.fanatik.com.tr/rss/anasayfa", "spor"),
    ("Orta Çizgi", "https://ortacizgi.com/feed", "spor"),
]

# Not: Buradaki liste ~23 kaynak ile başlıyor. "50 kaynak" hedefine ulaşmak
# için README'deki adımı takip ederek listeye kolayca yeni RSS linkleri
# ekleyebilirsin (her satır bir kaynak). Kaynak sayısı arttıkça eşik
# değerini (MIN_KAYNAK_SAYISI) de mantıklı şekilde ayarlaman gerekir.
