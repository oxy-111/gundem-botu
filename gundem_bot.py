# -*- coding: utf-8 -*-
"""
GÜNDEM BOTU
-----------
Ne yapar?
1) rss_kaynaklari.py içindeki tüm haber/spor sitelerinin RSS akışını okur.
2) Son X saat içinde yayınlanmış başlıkları toplar.
3) Birbirine çok benzeyen başlıkları (aynı haberin farklı kaynaklardaki
   versiyonları) tek bir "haber grubu" altında toplar.
4) Bir haber grubu MIN_KAYNAK_SAYISI kadar farklı kaynakta geçiyorsa
   "gündem" kabul edilir.
5) Bulunan gündem haberlerini docs/index.html adlı statik bir sayfaya yazar
   (kaynak listesiyle birlikte). GitHub Pages bu dosyayı otomatik yayınlar.

Bu script GitHub Actions tarafından her 30 dakikada bir otomatik çalıştırılır
(bkz. .github/workflows/gundem.yml). Kendi bilgisayarını açık tutmana gerek yok.
"""

import html
import os
import re
from datetime import datetime, timedelta, timezone
from time import mktime
from zoneinfo import ZoneInfo

import feedparser
from rapidfuzz import fuzz

from rss_kaynaklari import KAYNAKLAR

_ETIKET_TEMIZLE = re.compile(r"<[^>]+>")
_BOSLUK_TEMIZLE = re.compile(r"\s+")


def ozet_temizle(ham_metin, maks_uzunluk=550):
    """RSS özetindeki HTML etiketlerini temizler, 1-2 paragraflık kısa bir özet döndürür."""
    if not ham_metin:
        return ""
    metin = _ETIKET_TEMIZLE.sub(" ", ham_metin)
    metin = html.unescape(metin)
    metin = _BOSLUK_TEMIZLE.sub(" ", metin).strip()
    if len(metin) > maks_uzunluk:
        metin = metin[:maks_uzunluk].rsplit(" ", 1)[0] + "…"
    return metin

# ------------------- AYARLAR -------------------
MIN_KAYNAK_SAYISI = 15       # Bir haberin "gündem" sayılması için gereken min. farklı kaynak sayısı
SAAT_PENCERESI = 6           # Kaç saat içindeki haberleri dikkate alalım (RSS'ler her 30 dk okunacağı için geniş tutuldu)
BENZERLIK_ESIGI = 65         # 0-100 arası. Başlıklar bu oranın üstünde benzerse aynı haber sayılır
MAKS_GUNDEM_HABER = 10       # Maile en fazla kaç haber koyulsun
# -------------------------------------------------


def rss_oku():
    """Tüm kaynaklardan başlıkları toplar. Hatalı/erişilemeyen kaynağı atlar."""
    simdi = datetime.now(timezone.utc)
    sinir = simdi - timedelta(hours=SAAT_PENCERESI)
    tum_haberler = []

    for isim, url, kategori in KAYNAKLAR:
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                print(f"[UYARI] Okunamadı, atlanıyor: {isim}")
                continue

            for entry in feed.entries:
                baslik = entry.get("title", "").strip()
                link = entry.get("link", "")
                if not baslik:
                    continue

                # Yayın zamanı varsa filtre uygula, yoksa yine de dahil et
                yayin_zamani = None
                if entry.get("published_parsed"):
                    yayin_zamani = datetime.fromtimestamp(
                        mktime(entry.published_parsed), tz=timezone.utc
                    )
                elif entry.get("updated_parsed"):
                    yayin_zamani = datetime.fromtimestamp(
                        mktime(entry.updated_parsed), tz=timezone.utc
                    )

                if yayin_zamani and yayin_zamani < sinir:
                    continue

                ham_ozet = entry.get("summary", "") or entry.get("description", "")
                tum_haberler.append({
                    "baslik": baslik,
                    "link": link,
                    "kaynak": isim,
                    "kategori": kategori,
                    "ozet": ozet_temizle(ham_ozet),
                })
        except Exception as e:
            print(f"[HATA] {isim} okunamadı: {e}")
            continue

    print(f"Toplam {len(tum_haberler)} başlık toplandı ({len(KAYNAKLAR)} kaynaktan).")
    return tum_haberler


def haberleri_grupla(haberler):
    """Benzer başlıkları aynı grupta toplar. Her grup: {baslik, kaynaklar:set, linkler:list}"""
    gruplar = []

    for haber in haberler:
        eslesti = False
        for grup in gruplar:
            benzerlik = fuzz.token_set_ratio(haber["baslik"], grup["baslik"])
            if benzerlik >= BENZERLIK_ESIGI:
                grup["kaynaklar"].add(haber["kaynak"])
                grup["linkler"].append((haber["kaynak"], haber["link"]))
                # En uzun/dolu özeti gruba sakla (bazı kaynaklarda özet boş olabilir)
                if len(haber["ozet"]) > len(grup["ozet"]):
                    grup["ozet"] = haber["ozet"]
                eslesti = True
                break

        if not eslesti:
            gruplar.append({
                "baslik": haber["baslik"],
                "kaynaklar": {haber["kaynak"]},
                "linkler": [(haber["kaynak"], haber["link"])],
                "kategori": haber["kategori"],
                "ozet": haber["ozet"],
            })

    return gruplar


def gundem_filtrele(gruplar):
    """MIN_KAYNAK_SAYISI eşiğini geçen grupları, kaynak sayısına göre büyükten küçüğe sıralar."""
    gundem = [g for g in gruplar if len(g["kaynaklar"]) >= MIN_KAYNAK_SAYISI]
    gundem.sort(key=lambda g: len(g["kaynaklar"]), reverse=True)
    return gundem[:MAKS_GUNDEM_HABER]


def kategori_etiketi(kategori):
    return "SPOR" if kategori == "spor" else "GENEL / SİYASET"


def satir_render(grup, rank, maks_kaynak):
    kaynak_sayisi = len(grup["kaynaklar"])
    baslik = html.escape(grup["baslik"])
    etiket = kategori_etiketi(grup["kategori"])

    # Sinyal göstergesi: kaç kaynakta geçtiğini "teleks şeridi" gibi
    # dolu/boş çentiklerle gösteriyoruz (0'dan maks_kaynak'a kadar)
    TOPLAM_CENTIK = 20
    dolu = round((kaynak_sayisi / maks_kaynak) * TOPLAM_CENTIK) if maks_kaynak else 0
    dolu = max(1, min(TOPLAM_CENTIK, dolu))
    centikler = "".join(
        f'<span class="centik {"dolu" if i < dolu else ""}"></span>'
        for i in range(TOPLAM_CENTIK)
    )

    # Kaynak listesi (en altta, rozet/pill şeklinde, linkli)
    kaynak_pilleri = "".join(
        f'<a class="kaynak-pill" href="{html.escape(link)}" target="_blank" rel="noopener">{html.escape(kaynak)}</a>'
        for kaynak, link in sorted(grup["linkler"], key=lambda x: x[0])
    )

    ozet = html.escape(grup.get("ozet") or "").strip()
    if ozet:
        ozet_html = f'<p class="ozet-metin">{ozet}</p>'
    else:
        ozet_html = '<p class="ozet-metin ozet-yok">Bu haber için kaynaklardan özet metni alınamadı.</p>'

    return f"""
    <details class="haber">
      <summary class="haber-baslik-satiri">
        <div class="rank">{rank:02d}</div>
        <div class="haber-govde">
          <div class="ust-satir">
            <span class="etiket">{etiket}</span>
            <span class="sinyal-sayi">{kaynak_sayisi} KAYNAK</span>
          </div>
          <h2 class="baslik">{baslik}</h2>
          <div class="sinyal-metre">{centikler}</div>
        </div>
        <span class="ac-kapa-ikon" aria-hidden="true"></span>
      </summary>
      <div class="detay-panel">
        {ozet_html}
        <div class="kaynaklar">
          <span class="kaynaklar-etiket">Kaynaklar:</span>
          {kaynak_pilleri}
        </div>
      </div>
    </details>"""


def sayfa_olustur(gundem_listesi, toplam_kaynak, taranan_baslik):
    tz = ZoneInfo("Europe/Istanbul")
    simdi = datetime.now(tz).strftime("%d.%m.%Y — %H:%M")

    maks_kaynak = max((len(g["kaynaklar"]) for g in gundem_listesi), default=MIN_KAYNAK_SAYISI)

    if gundem_listesi:
        icerik_html = "".join(
            satir_render(g, i, maks_kaynak) for i, g in enumerate(gundem_listesi, 1)
        )
        durum_notu = f"{len(gundem_listesi)} başlık, en az {MIN_KAYNAK_SAYISI} kaynakta birden geçtiği için listelendi."
    else:
        icerik_html = f"""
        <div class="bos-durum">
          <p class="bos-baslik">Şu an eşiği geçen bir gündem yok.</p>
          <p class="bos-aciklama">Son tarama {taranan_baslik} başlığı inceledi, ama hiçbiri
          en az {MIN_KAYNAK_SAYISI} farklı kaynakta aynı anda geçmedi. Bot 30 dakika sonra
          tekrar tarayacak.</p>
        </div>"""
        durum_notu = "Şu anki eşiği geçen başlık yok."

    return f"""<!DOCTYPE html>
<html lang="tr" data-tema="koyu">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gündem Servisi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;800&family=Newsreader:ital,wght@0,400;0,500;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #16130f;
    --paper: #f2ead9;
    --paper-dim: #e7ddc7;
    --ink: #211a12;
    --amber: #ffb100;
    --rule: #55493a;
    --muted: #8c8071;
  }}
  html[data-tema="acik"] {{
    --bg: #f2ead9;
    --paper: #211a12;
    --paper-dim: #ffffff;
    --ink: #211a12;
    --amber: #a85e00;
    --rule: #d8cdb2;
    --muted: #6b5f4a;
  }}
  * {{ box-sizing: border-box; }}
  html {{ color-scheme: dark; }}
  html[data-tema="acik"] {{ color-scheme: light; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--paper);
    font-family: 'Newsreader', serif;
    padding: 0 0 6rem;
    transition: background 0.15s ease, color 0.15s ease;
  }}
  .masthead {{
    border-bottom: 3px solid var(--amber);
    padding: 2.2rem 1.5rem 1.4rem;
    max-width: 780px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }}
  .masthead-metin {{ min-width: 0; }}
  .tema-buton {{
    flex-shrink: 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--bg);
    background: var(--amber);
    border: none;
    border-radius: 3px;
    padding: 0.55rem 0.85rem;
    cursor: pointer;
  }}
  .tema-buton:hover {{ opacity: 0.85; }}
  .ticker {{
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.14em;
    color: var(--amber);
    text-transform: uppercase;
    margin-bottom: 0.6rem;
  }}
  .masthead h1 {{
    font-family: 'Big Shoulders Display', sans-serif;
    font-weight: 800;
    font-size: clamp(2.6rem, 7vw, 4.2rem);
    letter-spacing: 0.01em;
    margin: 0;
    line-height: 0.92;
    text-transform: uppercase;
  }}
  .masthead .alt-baslik {{
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
    color: var(--muted);
    margin-top: 0.7rem;
  }}
  main {{
    max-width: 780px;
    margin: 0 auto;
    padding: 0 1.5rem;
  }}
  .haber {{
    border-bottom: 1px solid var(--rule);
  }}
  .haber-baslik-satiri {{
    display: flex;
    gap: 1.1rem;
    padding: 1.7rem 0;
    cursor: pointer;
    list-style: none;
  }}
  .haber-baslik-satiri::-webkit-details-marker {{ display: none; }}
  .rank {{
    font-family: 'Big Shoulders Display', sans-serif;
    font-weight: 800;
    font-size: 2.3rem;
    color: var(--amber);
    line-height: 1;
    min-width: 2.4ch;
  }}
  .haber-govde {{ flex: 1; min-width: 0; }}
  .ust-satir {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    letter-spacing: 0.08em;
    color: var(--muted);
    text-transform: uppercase;
    margin-bottom: 0.5rem;
  }}
  .etiket {{ color: var(--amber); }}
  .baslik {{
    font-family: 'Newsreader', serif;
    font-weight: 500;
    font-size: 1.35rem;
    line-height: 1.28;
    margin: 0 0 0.9rem;
    color: var(--paper);
  }}
  .sinyal-metre {{
    display: flex;
    gap: 2px;
  }}
  .centik {{
    height: 10px;
    flex: 1;
    background: var(--rule);
    border-radius: 1px;
  }}
  .centik.dolu {{ background: var(--amber); }}
  .ac-kapa-ikon {{
    flex-shrink: 0;
    align-self: center;
    width: 0.6rem;
    height: 0.6rem;
    border-right: 2px solid var(--muted);
    border-bottom: 2px solid var(--muted);
    transform: rotate(45deg);
    transition: transform 0.2s ease;
  }}
  details[open] .ac-kapa-ikon {{ transform: rotate(-135deg); }}
  .detay-panel {{
    padding: 0 0 1.9rem 3.5ch;
  }}
  .ozet-metin {{
    font-family: 'Newsreader', serif;
    font-size: 1.02rem;
    line-height: 1.6;
    color: var(--paper);
    margin: 0 0 1rem;
  }}
  .ozet-metin.ozet-yok {{
    color: var(--muted);
    font-style: italic;
  }}
  .kaynaklar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
  }}
  .kaynaklar-etiket {{
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-right: 0.2rem;
  }}
  .kaynak-pill {{
    color: var(--bg);
    background: var(--paper-dim);
    padding: 0.22rem 0.55rem;
    border-radius: 3px;
    text-decoration: none;
    white-space: nowrap;
  }}
  .kaynak-pill:hover {{ background: var(--amber); }}
  .bos-durum {{
    padding: 3.5rem 0;
    text-align: center;
  }}
  .bos-baslik {{
    font-family: 'Big Shoulders Display', sans-serif;
    font-weight: 800;
    font-size: 1.6rem;
    text-transform: uppercase;
    color: var(--amber);
    margin-bottom: 0.6rem;
  }}
  .bos-aciklama {{
    color: var(--muted);
    max-width: 46ch;
    margin: 0 auto;
    font-size: 0.95rem;
  }}
  footer {{
    max-width: 780px;
    margin: 2rem auto 0;
    padding: 1.2rem 1.5rem 0;
    font-family: 'Space Mono', monospace;
    font-size: 0.65rem;
    color: var(--muted);
    letter-spacing: 0.05em;
  }}
</style>
</head>
<body>
  <div class="masthead">
    <div class="masthead-metin">
      <div class="ticker">SON GÜNCELLEME · {simdi} · {toplam_kaynak} KAYNAK TARANDI</div>
      <h1>Gündem Servisi</h1>
      <div class="alt-baslik">{durum_notu}</div>
    </div>
    <button class="tema-buton" id="tema-buton" onclick="temaDegistir()">☀ Aydınlık</button>
  </div>
  <main>
    {icerik_html}
  </main>
  <footer>
    Bu sayfa {toplam_kaynak} haber/spor kaynağının RSS akışı otomatik taranarak
    her 30 dakikada bir yeniden üretilir. Sıralama, bir başlığın kaç farklı
    kaynakta aynı anda geçtiğine göre yapılır. Bir haberin üstüne tıklayarak
    özetini açıp kapatabilirsin.
  </footer>
  <script>
    (function() {{
      var kayitliTema = localStorage.getItem('gundem-tema');
      if (kayitliTema) {{
        document.documentElement.setAttribute('data-tema', kayitliTema);
      }}
      guncelleButonMetni();
    }})();

    function temaDegistir() {{
      var mevcut = document.documentElement.getAttribute('data-tema');
      var yeni = mevcut === 'acik' ? 'koyu' : 'acik';
      document.documentElement.setAttribute('data-tema', yeni);
      localStorage.setItem('gundem-tema', yeni);
      guncelleButonMetni();
    }}

    function guncelleButonMetni() {{
      var mevcut = document.documentElement.getAttribute('data-tema');
      var buton = document.getElementById('tema-buton');
      if (!buton) return;
      buton.textContent = mevcut === 'acik' ? '● Karanlık' : '☀ Aydınlık';
    }}
  </script>
</body>
</html>"""


def main():
    haberler = rss_oku()
    if not haberler:
        print("Hiç başlık toplanamadı, önceki sayfa korunacak.")
        return

    gruplar = haberleri_grupla(haberler)
    gundem = gundem_filtrele(gruplar)

    sayfa = sayfa_olustur(gundem, len(KAYNAKLAR), len(haberler))

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(sayfa)

    print(f"Sayfa güncellendi: {len(gundem)} gündem haberi listelendi.")


if __name__ == "__main__":
    main()
