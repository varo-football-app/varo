import json, re, sys, os, unicodedata, urllib.request, urllib.parse, datetime as dt
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}
SLUGS = "afc.asian.cup afc.champions afc.cup alg.1 all arg.1 arg.copa aus.1 aut.1 bel.1 bol.copa bra.1 caf.champions caf.confed caf.nations campeones.cup chi.1 chn.1 col.1 col.copa concacaf.champions concacaf.leagues.cup conmebol.libertadores conmebol.sudamericana cze.1 den.1 egy.1 eng.1 eng.2 eng.charity eng.fa eng.trophy esp.1 esp.2 fifa.cwc fifa.friendly fifa.world fifa.worldq.caf fifa.worldq.uefa fra.1 fra.2 ger.1 ger.2 gre.1 ind.1 irq.1 ita.1 ita.2 jpn.1 ksa.1 ksa.kings.cup mar.1 mex.1 ned.1 ned.cup nor.1 por.1 por.taca.portugal qat.1 rsa.1 rus.1 sco.1 sco.cis sco.tennents sui.1 swe.1 tun.1 tur.1 uae.1 uefa.champions uefa.europa uefa.europa.conf uefa.nations uru.1 usa.1 usa.open".split()
def get(u, t=20):
    return urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=t).read().decode("utf-8", "ignore")
def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(fc|sc|cd|ac|as|cf|fk|club|sporting|sportif|association|associacao|de|do|da|the|f\.c\.|s\.c\.)\b", " ", s)
    return [w for w in re.sub(r"[^a-z0-9 ]", " ", s).split() if w]
ALIAS = {'Petro de Luanda': 'Petroleos Luanda', 'Raja': 'Raja Club Athletic', 'Raja Casablanca': 'Raja Club Athletic', 'RSB Berkane': 'Renaissance de Berkane', 'Al Hilal Omdurman': 'Al-Hilal Omdurman', 'Omdurman': 'Al-Hilal Omdurman', 'Simba': 'Simba SC', 'CD Primeiro': 'Primeiro de Agosto', 'Club Sportif': 'Club Sportif Sfaxien'}
FIX = {'CD Primeiro de Agosto': '14503', 'CD Primeiro': '14503', 'Primeiro de Agosto': '14503'}
def tm_find(name):
    if name in FIX: return 'https://tmssl.akamaized.net/images/wappen/head/%s.png' % FIX[name]
    name = ALIAS.get(name, name)
    h = get("https://www.transfermarkt.com/schnellsuche/ergebnis/schnellsuche?query=" + urllib.parse.quote(name))
    want = set(norm(name))
    for m in re.finditer(r'<a title="([^"]+)" href="/[^"]*/startseite/verein/(\d+)"', h):
        got = set(norm(m.group(1)))
        pm = lambda A, B: all(any(a == b or (len(a) >= 4 and (b.startswith(a) or a.startswith(b))) for b in B) for a in A)
        if want and got and (pm(want, got) or pm(got, want)):
            return "https://tmssl.akamaized.net/images/wappen/head/%s.png" % m.group(2)
    return ""
def main():
    path = "logos.json"
    L = json.load(open(path)) if os.path.exists(path) else {}
    miss = {}
    today = dt.date.today()
    from concurrent.futures import ThreadPoolExecutor
    def one(args):
        sl, d = args
        try:
            return json.loads(get("https://site.api.espn.com/apis/site/v2/sports/soccer/%s/scoreboard?dates=%s" % (sl, (today + dt.timedelta(days=d)).strftime("%Y%m%d")), 15))
        except Exception:
            return {}
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(one, [(sl, d) for sl in SLUGS for d in range(0, 4)]))
    for j in res:
        for e in j.get("events", []):
            for c in (e.get("competitions") or [{}])[0].get("competitors", []):
                t = c.get("team") or {}
                if not t.get("logo") and not (t.get("logos") or [{}])[0].get("href"):
                    for k in {t.get("displayName"), t.get("shortDisplayName"), t.get("name")}:
                        if k: miss.setdefault(k, t.get("displayName") or k)
    done = {}
    for k, full in miss.items():
        if k in L and L[k]:
            continue
        if full in done:
            L[k] = done[full]; continue
        try:
            u = tm_find(full) or (tm_find(k) if k != full else "")
        except Exception:
            u = ""
        done[full] = u
        if u:
            L[k] = u
    json.dump({k: v for k, v in L.items() if v}, open(path, "w"), ensure_ascii=False, indent=0, sort_keys=True)
    print("missing", len(miss), "logos", len(L))
    for k in miss:
        if not L.get(k): print("NOLOGO", k)
main()
