import json, re, hashlib, html, sys, urllib.request, urllib.parse, xml.etree.ElementTree as ET
UA = {"User-Agent": "Mozilla/5.0 (compatible; VaroNewsBot/1.0)", "Accept": "application/rss+xml, application/xml, text/xml, */*"}
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25)
    return r.read().decode("utf-8", "ignore")
def clean(t):
    t = re.sub(r"<[^>]+>", " ", t or "")
    return re.sub(r"\s+", " ", html.unescape(t)).strip()
import email.utils, datetime as _dt
def pubts(v):
    try:
        return email.utils.parsedate_to_datetime(v).astimezone(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return ""
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
            out.append({"id": "n" + hashlib.md5(link.encode()).hexdigest()[:12], "title": title, "summary": summ[:400], "image": img, "url": link, "source": src, "cat": clean(it.findtext("category")), "ts": pubts(it.findtext("pubDate"))})
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

import os, datetime
AHTS = {}
def ahly_text(u):
    try:
        h = get(u)
        m = re.search(r'datePublished"?:"(20[\d\-T:.]+Z)', h)
        AHTS[u] = m.group(1)[:19] + "Z" if m else ""
        ps = [clean(t) for t in re.findall(r"<p[^>]*>(.*?)</p>", h, re.S)]
        return " ".join(p for p in ps if len(p) > 25 and "{" not in p)[:1200]
    except Exception:
        return ""
def espn():
    out = []
    for s in ["uefa.champions", "eng.1", "esp.1", "ita.1", "ger.1"]:
        try:
            j = json.loads(urllib.request.urlopen(urllib.request.Request("https://site.api.espn.com/apis/site/v2/sports/soccer/%s/news?limit=10" % s, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read().decode("utf-8", "ignore"))
        except Exception as e:
            print("FAIL espn", s, e, file=sys.stderr); continue
        for a in j.get("articles", []):
            im = [x.get("url") for x in a.get("images", []) if x.get("url", "").startswith("https://a.espncdn.com/photo")]
            t = a.get("headline", "")
            if not im or re.search(r"Highlights|Watch|VAR review|Transfer rumors", t): continue
            out.append({"id": "w" + str(a["id"]), "src_title": t, "text": a.get("description", ""), "image": im[0], "source": "ESPN", "ts": (a.get("published") or "")[:19] + "Z" if a.get("published") else ""})
    return dedupe2(out)
def dedupe2(l):
    seen, o = set(), []
    for x in l:
        if x["id"] not in seen:
            seen.add(x["id"]); o.append(x)
    return o
ah = ahly(); zm = items("https://www.zamaleksc.com/feed.xml", "نادي الزمالك (الموقع الرسمي)", "zamalek")
IL_RE = re.compile(r'hapoel|maccabi|beitar|israel|sakhnin|هبوعيل|هابويل|مكابي|ميكابي|بيتار|إسرائيل|اسرائيل|سخنين', re.I)
cand = []
for x in mix(ah[:12], zm[:20]):
    _t = x["summary"] or ahly_text(x["url"])
    if not x.get("ts") and x["url"] not in AHTS: ahly_text(x["url"])
    x["ts"] = x.get("ts") or AHTS.get(x["url"], "")
    cand.append({"id": x["id"], "src_title": x["title"], "text": _t, "image": x["image"], "source": x["source"], "grp": "egypt", "ts": x.get("ts", "")})
for x in espn()[:30]:
    x["grp"] = "world"; cand.append(x)
if len(cand) < 5:
    print("too few candidates, keeping old file", file=sys.stderr); sys.exit(0)
cand = [c for c in cand if not IL_RE.search(c['src_title'] + ' ' + c['text'])]
_cut = (_dt.datetime.utcnow() - _dt.timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
cand = [c for c in cand if c.get("ts") and c["ts"] >= _cut]
cand.sort(key=lambda c: c["ts"], reverse=True)
rw = json.load(open("rewrites.json", encoding="utf-8")) if os.path.exists("rewrites.json") else {}
res = {"egypt": [], "world": [], "arab": []}
seen_t = set()
for c in cand:
    r = rw.get(c["id"])
    if not r: continue
    if r["t"] in seen_t: continue
    seen_t.add(r["t"])
    res[c["grp"]].append({"id": c["id"], "title": r["t"], "body": r["b"], "image": c["image"], "source": c["source"], "ts": c["ts"]})
json.dump(cand, open("cand.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
try:
    old = json.load(open("news.json", encoding="utf-8")); old.pop("updated", None)
except Exception:
    old = None
if old != res and (res["egypt"] or res["world"]):
    res["updated"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    json.dump(res, open("news.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("updated", len(res["egypt"]), len(res["world"]), file=sys.stderr)
print("pending rewrite:", [c["id"] for c in cand if c["id"] not in rw], file=sys.stderr)
