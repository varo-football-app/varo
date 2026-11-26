import json, re, hashlib, html, sys, urllib.request, urllib.parse, xml.etree.ElementTree as ET
UA = {"User-Agent": "Mozilla/5.0 (compatible; VaroNewsBot/1.0)", "Accept": "application/rss+xml, application/xml, text/xml, */*"}
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
    return r.read().decode("utf-8", "ignore")
def clean(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()
def items(url, src, kind):
    out = []
    try:
        root = ET.fromstring(get(url).strip())
    except Exception as e:
        print("FAIL", src, url, e, file=sys.stderr)
        return out
    for it in root.iter("item"):
        title = clean(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        d = it.findtext("description") or ""
        img = ""
        enc = it.find("enclosure")
        if enc is not None and enc.get("url"):
            img = enc.get("url")
        m = re.search(r'<img[^>]+src="([^"]+)"', d)
        if not img and m:
            img = m.group(1)
        if kind == "youm7":
            d = d.split("</br>")[0]
        summ = clean(d)
        if kind == "youm7" and re.search(r"الجودو|السلة|كرة اليد|الطائرة|السباحة|التنس|الإسكواش|الاسكواش|المصارعة|الجمباز|الملاكمة|الكاراتيه|التايكوندو|الفروسية|رفع الأثقال|الشطرنج|الأولمبية", title + " " + summ):
            continue
        if title and link and img.startswith("http"):
            out.append({"id": "n" + hashlib.md5(link.encode()).hexdigest()[:12], "title": title, "summary": summ[:400], "image": img, "url": link, "source": src, "cat": clean(it.findtext("category"))})
    print(src, len(out), file=sys.stderr)
    return out
def dedupe(l):
    seen, o = set(), []
    for x in l:
        k = x["title"][:40]
        if k not in seen:
            seen.add(k); o.append(x)
    return o
def mix(*qs):
    o = []
    for i in range(max(len(q) for q in qs)):
        for q in qs:
            if i < len(q): o.append(q[i])
    return o
def ahly():
    out = []
    try:
        h = get("https://www.alahlyegypt.com/ar/news")
    except Exception as e:
        print("FAIL ahly", e, file=sys.stderr); return out
    seen = set()
    for m in re.finditer(r'<a [^>]*href="(/ar/news/article/[^"]+)"[^>]*>(.*?)</a>', h, re.S):
        href, inner = m.group(1), m.group(2)
        if href in seen: continue
        seen.add(href)
        im = re.search(r'src="/_next/image\?url=([^&"]+)', inner)
        alts = [a for a in re.findall(r'alt="([^"]+)"', inner) if a.strip()]
        title = clean(alts[-1]) if alts else clean(inner)
        if not im or not title: continue
        img = urllib.parse.unquote(im.group(1))
        if not img.startswith("http"): continue
        link = "https://www.alahlyegypt.com" + urllib.parse.quote(urllib.parse.unquote(href), safe="/:%")
        out.append({"id": "n" + hashlib.md5(link.encode()).hexdigest()[:12], "title": title, "summary": "", "image": img, "url": link, "source": "النادي الأهلي (الموقع الرسمي)", "cat": ""})
    print("ahly", len(out), file=sys.stderr)
    return out
ah = ahly()
zm = items("https://www.zamaleksc.com/feed.xml", "نادي الزمالك (الموقع الرسمي)", "zamalek")
egypt = dedupe(mix(ah, zm))[:40]
new = {"egypt": egypt, "arab": []}
try:
    old = json.load(open("news.json", encoding="utf-8"))
    old.pop("updated", None)
except Exception:
    old = None
if not egypt:
    print("no items fetched, keeping old file", file=sys.stderr); sys.exit(0)
if old != new:
    new["updated"] = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    json.dump(new, open("news.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("updated", len(egypt), file=sys.stderr)
