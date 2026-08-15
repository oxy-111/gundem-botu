# -*- coding: utf-8 -*-
import html
import os
import re
import socket
from datetime import datetime, timedelta, timezone
from time import mktime
from zoneinfo import ZoneInfo

import feedparser
from rapidfuzz import fuzz

from rss_kaynaklari import KAYNAKLAR

# Bağlantı kilitlenmelerini önlemek için zaman aşımı
socket.setdefaulttimeout(10)

# ------------------- AYARLAR -------------------
MIN_KAYNAK_SAYISI = 3       # Gündem sayılması için min. kaynak sayısı
SAAT_PENCERESI = 8          # İncelenecek son saat penceresi
BENZERLIK_ESIGI = 65        # Başlık benzerlik eşiği
MAKS_HABER = 15             # Kategori başına listelenecek maks. haber sayısı
# -------------------------------------------------


def html_temizle(metin):
    """HTML etiketlerini ve fazla boşlukları temizler."""
    if not metin:
        return ""
    temiz = re.sub(r"<[^>]+>", "", metin)
    return " ".join(temiz.split()).strip()


def rss_oku():
    simdi = datetime.now(timezone.utc)
    sinir = simdi - timedelta(hours=SAAT_PENCERESI)
    tum_haberler = []

    for isim, url, kategori in KAYNAKLAR:
        try:
            feed = feedparser.parse(url, agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            if feed.bozo and not feed.entries:
                continue

            for entry in feed.entries:
                baslik = entry.get("title", "").strip()
                link = entry.get("link", "")
                if not baslik:
                    continue

                # Haber özetini (açıklamasını) çek ve temizle
                ozet_ham = entry.get("summary") or entry.get("description") or ""
                ozet = html_temizle(ozet_ham)

                yayin_zamani = None
                if entry.get("published_parsed"):
                    yayin_zamani = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)
                elif entry.get("updated_parsed"):
                    yayin_zamani = datetime.fromtimestamp(mktime(entry.updated_parsed), tz=timezone.utc)

                if yayin_zamani and yayin_zamani < sinir:
                    continue

                tum_haberler.append({
                    "baslik": baslik,
                    "link": link,
                    "ozet": ozet,
                    "kaynak": isim,
                    "kategori": kategori,
                })
        except Exception:
            continue

    return tum_haberler


def haberleri_grupla(haberler):
    gruplar = []
    for haber in haberler:
        eslesti = False
        for grup in gruplar:
            if grup["kategori"] == haber["kategori"]:
                benzerlik = fuzz.token_set_ratio(haber["baslik"], grup["baslik"])
                if benzerlik >= BENZERLIK_ESIGI:
                    grup["kaynaklar"].add(haber["kaynak"])
                    grup["link_dict"][haber["kaynak"]] = haber["link"]
                    # En detaylı/uzun özeti grupta sakla
                    if len(haber["ozet"]) > len(grup["ozet"]):
                        grup["ozet"] = haber["ozet"]
                    eslesti = True
                    break

        if not eslesti:
            gruplar.append({
                "baslik": haber["baslik"],
                "ozet": haber["ozet"],
                "kaynaklar": {haber["kaynak"]},
                "link_dict": {haber["kaynak"]: haber["link"]},
                "kategori": haber["kategori"],
            })
    return gruplar


def kategori_filtrele(gruplar, kategori_adi):
    filtreli = [g for g in gruplar if g["kategori"] == kategori_adi and len(g["kaynaklar"]) >= MIN_KAYNAK_SAYISI]
    filtreli.sort(key=lambda g: len(g["kaynaklar"]), reverse=True)
    return filtreli[:MAKS_HABER]


def satir_render(grup, rank, maks_kaynak):
    kaynak_sayisi = len(grup["kaynaklar"])
    baslik = html.escape(grup["baslik"])
    kategori_etiket = grup["kategori"].upper()
    ozet_metni = html.escape(grup["ozet"]) if grup["ozet"] else "Bu haber için detay metni bulunmuyor."

    TOPLAM_CENTIK = 15
    dolu = round((kaynak_sayisi / maks_kaynak) * TOPLAM_CENTIK) if maks_kaynak else 1
    dolu = max(1, min(TOPLAM_CENTIK, dolu))
    centikler = "".join(f'<span class="centik {"dolu" if i < dolu else ""}"></span>' for i in range(TOPLAM_CENTIK))

    kaynak_pilleri = "".join(
        f'<a class="kaynak-pill" href="{html.escape(link)}" target="_blank" rel="noopener">{html.escape(kaynak)}</a>'
        for kaynak, link in sorted(grup["link_dict"].items())
    )

    return f"""
    <article class="haber">
      <div class="rank">{rank:02d}</div>
      <div class="haber-govde">
        <div class="ust-satir">
          <span class="etiket">{kategori_etiket}</span>
          <span class="sinyal-sayi">{kaynak_sayisi} KAYNAK</span>
        </div>
        <h2 class="baslik">{baslik}</h2>
        <div class="sinyal-metre">{centikler}</div>
        
        <details class="detay-alani">
          <summary class="detay-buton">DETAY OKU</summary>
          <div class="detay-icerik">
            <p>{ozet_metni}</p>
          </div>
        </details>

        <div class="kaynaklar">
          <span class="kaynaklar-etiket">Kaynaklar:</span>
          {kaynak_pilleri}
        </div>
      </div>
    </article>"""


def liste_html_uret(haber_listesi, kategori_adi):
    if not haber_listesi:
        return f"""
        <div class="bos-durum">
          <p class="bos-baslik">{kategori_adi.upper()} İÇİN EŞİĞİ GEÇEN HABER YOK</p>
          <p class="bos-aciklama">Son taramada en az {MIN_KAYNAK_SAYISI} farklı kaynakta ortak yer alan bir haber bulunamadı.</p>
        </div>"""

    maks_kaynak = max(len(g["kaynaklar"]) for g in haber_listesi)
    return "".join(satir_render(g, i, maks_kaynak) for i, g in enumerate(haber_listesi, 1))


def sayfa_olustur(genel_h, siyaset_h, futbol_h, toplam_kaynak):
    tz = ZoneInfo("Europe/Istanbul")
    simdi = datetime.now(tz).strftime("%d.%m.%Y — %H:%M")

    genel_icerik = liste_html_uret(genel_h, "Genel")
    siyaset_icerik = liste_html_uret(siyaset_h, "Siyaset")
    futbol_icerik = liste_html_uret(futbol_h, "Futbol")

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gündem Servisi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;800&family=Newsreader:ital,wght@0,400;0,500;1,400&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #0a0a0a;
    --card-bg: #121212;
    --text-primary: #ededed;
    --text-muted: #888888;
    --border-color: #222222;
    --pill-bg: #1e1e1e;
    --pill-text: #cccccc;
    --amber: #ffb100;
  }}

  body.light-mode {{
    --bg: #ffffff;
    --card-bg: #f8f9fa;
    --text-primary: #111111;
    --text-muted: #666666;
    --border-color: #e5e7eb;
    --pill-bg: #f1f3f5;
    --pill-text: #111111;
    --amber: #d97706;
  }}

  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--text-primary);
    font-family: 'Newsreader', serif;
    padding: 0 0 6rem;
    transition: background-color 0.2s ease, color 0.2s ease;
  }}

  .masthead {{
    border-bottom: 2px solid var(--amber);
    padding: 2rem 1.5rem 1.4rem;
    max-width: 780px;
    margin: 0 auto;
  }}
  .masthead-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.6rem;
  }}
  .ticker {{
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    color: var(--amber);
    text-transform: uppercase;
  }}
  .theme-btn {{
    background: var(--amber);
    color: var(--bg);
    border: none;
    padding: 0.35rem 0.7rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    cursor: pointer;
    border-radius: 3px;
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

  .tabs {{
    display: flex;
    gap: 0.5rem;
    max-width: 780px;
    margin: 1.5rem auto 0;
    padding: 0 1.5rem;
  }}
  .tab-btn {{
    background: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-muted);
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    padding: 0.6rem 1.2rem;
    cursor: pointer;
    text-transform: uppercase;
    transition: all 0.2s ease;
    border-radius: 2px;
  }}
  .tab-btn:hover {{ border-color: var(--amber); color: var(--text-primary); }}
  .tab-btn.active {{
    background: var(--amber);
    border-color: var(--amber);
    color: var(--bg);
  }}

  main {{
    max-width: 780px;
    margin: 0 auto;
    padding: 0 1.5rem;
  }}
  .tab-content {{ display: none; }}
  .tab-content.active {{ display: block; }}

  .haber {{
    display: flex;
    gap: 1.1rem;
    padding: 1.7rem 0;
    border-bottom: 1px solid var(--border-color);
  }}
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
    color: var(--text-muted);
    text-transform: uppercase;
    margin-bottom: 0.5rem;
  }}
  .etiket {{ color: var(--amber); }}
  .baslik {{
    font-family: 'Newsreader', serif;
    font-weight: 500;
    font-size: 1.35rem;
    line-height: 1.3;
    margin: 0 0 0.8rem;
    color: var(--text-primary);
  }}

  .sinyal-metre {{
    display: flex;
    gap: 3px;
    margin-bottom: 0.9rem;
  }}
  .centik {{
    height: 7px;
    flex: 1;
    background: var(--border-color);
    border-radius: 1px;
  }}
  .centik.dolu {{ background: var(--amber); }}

  /* Detay Oku (Accordion) */
  .detay-alani {{
    margin: 0.8rem 0;
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    overflow: hidden;
  }}
  .detay-buton {{
    font-family: 'Space Mono', monospace;
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--amber);
    padding: 0.5rem 0.8rem;
    cursor: pointer;
    user-select: none;
  }}
  .detay-icerik {{
    padding: 0 0.8rem 0.8rem;
    font-family: 'Newsreader', serif;
    font-size: 1.05rem;
    line-height: 1.5;
    color: var(--text-primary);
  }}
  .detay-icerik p {{ margin: 0; }}

  .kaynaklar {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem;
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
  }}
  .kaynaklar-etiket {{
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-right: 0.2rem;
  }}
  .kaynak-pill {{
    color: var(--pill-text);
    background: var(--pill-bg);
    padding: 0.25rem 0.55rem;
    border: 1px solid var(--border-color);
    border-radius: 3px;
    text-decoration: none;
    white-space: nowrap;
  }}
  .kaynak-pill:hover {{
    background: var(--amber);
    color: var(--bg);
    border-color: var(--amber);
  }}

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
    color: var(--text-muted);
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
    color: var(--text-muted);
    letter-spacing: 0.05em;
  }}
</style>
</head>
<body>
  <div class="masthead">
    <div class="masthead-top">
      <div class="ticker">SON GÜNCELLEME · {simdi} · {toplam_kaynak} KAYNAK TARANDI</div>
      <button id="theme-btn" class="theme-btn" onclick="temaDegistir()">☀ AYDINLIK</button>
    </div>
    <h1>Gündem Servisi</h1>
  </div>

  <div class="tabs">
    <button class="tab-btn active" onclick="tabSec(event, 'genel')">Genel ({len(genel_h)})</button>
    <button class="tab-btn" onclick="tabSec(event, 'siyaset')">Siyaset ({len(siyaset_h)})</button>
    <button class="tab-btn" onclick="tabSec(event, 'futbol')">Futbol ({len(futbol_h)})</button>
  </div>

  <main>
    <div id="tab-genel" class="tab-content active">{genel_icerik}</div>
    <div id="tab-siyaset" class="tab-content">{siyaset_icerik}</div>
    <div id="tab-futbol" class="tab-content">{futbol_icerik}</div>
  </main>

  <footer>
    Haberler her 30 dakikada bir güncellenir. En az {MIN_KAYNAK_SAYISI} bağımsız kaynakta yer alan başlıklar listelenir.
  </footer>

  <script>
    function tabSec(e, kategori) {{
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      
      e.currentTarget.classList.add('active');
      document.getElementById('tab-' + kategori).classList.add('active');
    }}

    function temaDegistir() {{
      const body = document.body;
      const btn = document.getElementById('theme-btn');
      body.classList.toggle('light-mode');
      
      if (body.classList.contains('light-mode')) {{
        btn.innerText = '🌙 KARANLIK';
        localStorage.setItem('tema', 'light');
      }} else {{
        btn.innerText = '☀ AYDINLIK';
        localStorage.setItem('tema', 'dark');
      }}
    }}

    (function() {{
      if (localStorage.getItem('tema') === 'light') {{
        document.body.classList.add('light-mode');
        document.getElementById('theme-btn').innerText = '🌙 KARANLIK';
      }}
    }})();
  </script>
</body>
</html>"""


def main():
    haberler = rss_oku()
    if not haberler:
        return

    gruplar = haberleri_grupla(haberler)
    
    genel_gundem = kategori_filtrele(gruplar, "genel")
    siyaset_gundem = kategori_filtrele(gruplar, "siyaset")
    futbol_gundem = kategori_filtrele(gruplar, "futbol")

    sayfa = sayfa_olustur(genel_gundem, siyaset_gundem, futbol_gundem, len(KAYNAKLAR))

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(sayfa)


if __name__ == "__main__":
    main()
