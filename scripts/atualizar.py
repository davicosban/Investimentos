#!/usr/bin/env python3
"""Atualiza os dados do Painel Investimentos (br.json, us.json, hist.json e o bloco MACRO do index.html).

Uso: python3 atualizar.py <pasta-do-site>
Precisa de acesso de rede a: www.fundamentus.com.br, brapi.dev, api.nasdaq.com,
query1.finance.yahoo.com, api.bcb.gov.br. Se uma fonte falhar, mantém o arquivo anterior.
"""
import json, re, sys, os, time, html, datetime, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

SITE = sys.argv[1] if len(sys.argv) > 1 else "."
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
      "Accept": "application/json, text/html, */*", "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
      "Cache-Control": "no-cache", "Pragma": "no-cache"}

def get(url, tries=2):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
                b = r.read()
                enc = r.headers.get_content_charset() or "utf-8"
                return b.decode(enc, "replace")
        except Exception as e:
            err = e; time.sleep(2 * (i + 1))
    raise err

def jget(url): return json.loads(get(url))
def load(name, default):
    try: return json.load(open(os.path.join(SITE, name)))
    except Exception: return default
def save(name, obj):
    json.dump(obj, open(os.path.join(SITE, name), "w"), separators=(",", ":"), ensure_ascii=False)

SECT = {'Finance':'Financeiro','Utilities':'Utilidade pública','Producer Manufacturing':'Bens industriais','Process Industries':'Indústria de base','Retail Trade':'Varejo','Non-Energy Minerals':'Mineração e siderurgia','Consumer Durables':'Bens duráveis','Transportation':'Transporte','Commercial Services':'Serviços comerciais','Consumer Non-Durables':'Consumo não cíclico','Industrial Services':'Serviços industriais','Distribution Services':'Distribuição','Consumer Services':'Serviços ao consumidor','Health Services':'Saúde','Technology Services':'Tecnologia','Communications':'Telecomunicações','Energy Minerals':'Petróleo e gás','Electronic Technology':'Tecnologia','Health Technology':'Saúde','Miscellaneous':'Outros',
        'Technology':'Tecnologia','Consumer Discretionary':'Consumo cíclico','Health Care':'Saúde','Industrials':'Indústria','Energy':'Energia','Consumer Staples':'Consumo não cíclico','Real Estate':'Imobiliário','Basic Materials':'Materiais básicos','Telecommunications':'Telecomunicações','':'Outros'}
log = []

# ---------- Brasil ----------
def num(s):
    s = html.unescape(re.sub("<[^>]+>", "", s)).strip().replace("%", "").replace(".", "").replace(",", ".")
    try: return float(s)
    except ValueError: return 0.0

def fundamentus():
    t = get("https://www.fundamentus.com.br/resultado.php")
    body = t[t.find("<tbody"):]
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)
        if len(tds) < 22: continue
        tk = re.sub("<[^>]+>", "", tds[0]).strip()
        rows.append([tk] + [num(x) for x in tds[1:22]])
    return {r[0]: r for r in rows if r[1] > 0 and r[18] > 0}

def brapi():
    j = jget("https://brapi.dev/api/quote/list?type=stock&limit=1000")
    return {s["stock"]: s for s in j["stocks"]}

# ---------- EUA ----------
def nasdaq():
    j = jget("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=10000&download=true")
    out = []
    for r in j["data"]["rows"]:
        try: mc = float(r["marketCap"] or 0)
        except ValueError: continue
        if mc < 2e9 or re.search(r"[\^/]", r["symbol"]): continue
        name = re.sub(r" (Class [A-C] )?(Common Stock|Ordinary Shares|American Depositary Shares).*$", "", r["name"])[:60]
        def f(x):
            try: return float(str(x).replace("$", "").replace("%", "").replace(",", ""))
            except ValueError: return None
        out.append({"t": r["symbol"], "n": name, "p": f(r["lastsale"]), "c": f(r["pctchange"]), "v": f(r["volume"]),
                    "mc": round(mc / 1e6), "s": SECT.get(r["sector"], r["sector"] or "Outros"), "i": r["industry"], "co": r["country"]})
    out.sort(key=lambda r: -r["mc"])
    return [r for r in out if r["t"] not in ("GOOGM", "GOOGN", "CCZ")]

# ---------- Histórico (Yahoo) ----------
LONG = {}
def chart(sym):
    """Um pedido só por ativo: histórico diário completo. Guarda 1 ano em hist.json e o resto (semanal) em LONG."""
    j = jget("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + "?range=max&interval=1d")
    x = j["chart"]["result"][0]; m = x["meta"]; c = x["indicators"]["quote"][0]["close"]
    off = m.get("gmtoffset") or 0
    allp = [((ts + off) // 86400, float("%.5g" % v)) for ts, v in zip(x["timestamp"], c) if v is not None]
    if m.get("dataGranularity", "1d") != "1d" or len(allp) < 2:
        j = jget("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + "?range=1y&interval=1d")
        x = j["chart"]["result"][0]; m = x["meta"]; c = x["indicators"]["quote"][0]["close"]
        off = m.get("gmtoffset") or 0
        pts = [((ts + off) // 86400, float("%.5g" % v)) for ts, v in zip(x["timestamp"], c) if v is not None]
    else:
        pts = [p for p in allp if p[0] >= allp[-1][0] - 366]
        wk = {}
        for d, v in allp: wk[(d + 3) // 7] = (d, v)   # último fechamento de cada semana
        w = [wk[k] for k in sorted(wk)]
        if len(w) > 1:
            LONG[sym.replace(".SA", "")] = {"d0": w[0][0], "dd": [w[i][0] - w[i - 1][0] for i in range(1, len(w))], "c": [v for _, v in w]}
    days = [p[0] for p in pts]
    return {"n": m.get("longName") or m.get("shortName"), "hi": m.get("fiftyTwoWeekHigh"), "lo": m.get("fiftyTwoWeekLow"),
            "p": m.get("regularMarketPrice"), "pc": m.get("chartPreviousClose"), "t": m.get("regularMarketTime"),
            "d0": days[0], "dd": [days[i] - days[i - 1] for i in range(1, len(days))], "c": [p[1] for p in pts]}

# ---------- Histórico longo e intradiário (um arquivo por ativo em hx/) ----------
def fname(sym): return re.sub(r"[^A-Za-z0-9]", "_", sym) + ".json"

def yraw(sym, rng, itv):
    url = ("https://query2.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + f"?range={rng}&interval={itv}&includePrePost=false")
    for i in range(2):
        try:
            j = jget(url); break
        except Exception as e:
            err = e; time.sleep(20 if "429" in str(e) else 3)
    else:
        raise err
    x = j["chart"]["result"][0]
    return [(ts, float("%.5g" % v)) for ts, v in zip(x.get("timestamp") or [], x["indicators"]["quote"][0]["close"]) if v is not None]

def intraday(sym):
    pts = yraw(sym, "5d", "15m")
    if len(pts) < 2: return None
    return {"t0": pts[0][0], "dt": [round((pts[i][0] - pts[i - 1][0]) / 60) for i in range(1, len(pts))], "c": [v for _, v in pts]}

# ---------- Câmbio (moedas em reais) ----------
FX = ["USDBRL=X", "EURBRL=X", "GBPBRL=X", "ARSBRL=X", "CHFBRL=X", "JPYBRL=X", "CNYBRL=X", "CADBRL=X", "AUDBRL=X", "MXNBRL=X", "CLPBRL=X", "UYUBRL=X"]

# ---------- Banco Central ----------
def bcb(code, n):
    return jget(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados/ultimos/{n}?formato=json")

def bcbrange(code, years):
    hoje = datetime.date.today(); ini = hoje - datetime.timedelta(days=int(years * 365.25) - 2)
    return jget(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json&dataInicial={ini:%d/%m/%Y}&dataFinal={hoje:%d/%m/%Y}")

def macrohist():
    out = {}
    for key, code, yrs in (("selic", 432, 9.9), ("cdi", 4389, 9.9), ("ptax", 1, 9.9), ("ipca12", 13522, 26), ("poup", 195, 9.9)):
        rows = bcbrange(code, yrs); pts = []
        for r in rows:
            try:
                d, mth, y = r["data"].split("/"); day = (datetime.date(int(y), int(mth), int(d)) - datetime.date(1970, 1, 1)).days
                pts.append((day, float(r["valor"])))
            except (ValueError, KeyError): pass
        # séries diárias que quase não mudam (Selic, CDI): guarda só quando muda + 1 ponto por semana
        if key in ("selic", "cdi"):
            keep = [p for i, p in enumerate(pts) if i == 0 or i == len(pts) - 1 or p[1] != pts[i - 1][1] or (p[0] - pts[i - 1][0]) >= 7 or p[0] % 7 == 0]
            pts = keep
        if len(pts) > 1:
            out[key] = {"d0": pts[0][0], "dd": [pts[i][0] - pts[i - 1][0] for i in range(1, len(pts))], "c": [v for _, v in pts]}
        time.sleep(0.5)
    return out

def main():
    old_br, old_us, old_h = load("br.json", []), load("us.json", []), load("hist.json", {})
    # Brasil
    try:
        fr = fundamentus(); log.append(f"Fundamentus: {len(fr)} ações")
    except Exception as e:
        fr = None; log.append(f"Fundamentus FALHOU: {e}")
    try:
        bl = brapi(); log.append(f"brapi: {len(bl)} ações")
    except Exception as e:
        bl = None; log.append(f"brapi FALHOU: {e}")
    if fr is None and bl is None:
        br = old_br
    else:
        fr = fr or {}; bl = bl or {}
        oldmap = {r["t"]: r for r in old_br}
        br = []
        for t in sorted(set(fr) | set(bl)):
            f, b = fr.get(t), bl.get(t)
            price = (b or {}).get("close") or (f[1] if f else None)
            if not price: continue
            lq = f[18] if f else None
            if not lq and not (b and b.get("volume")): continue
            name = (b or {}).get("name") or oldmap.get(t, {}).get("n", "")
            if name and name.isupper(): name = name.title()
            row = {"t": t, "n": name, "s": SECT.get((b or {}).get("sector") or "", (b or {}).get("sector") or oldmap.get(t, {}).get("s", "Outros")),
                   "p": round(price, 2), "c": round(b["change"], 2) if b and b.get("change") is not None else None,
                   "mc": round(b["market_cap"] / 1e6) if b and b.get("market_cap") else oldmap.get(t, {}).get("mc"),
                   "lq": round(lq) if lq else oldmap.get(t, {}).get("lq")}
            if f:
                for k, i in dict(pl=2, pvp=3, psr=4, dy=5, evebit=10, evebitda=11, mb=12, mebit=13, ml=14, lc=15, roic=16, roe=17, pla=19, dlpl=20, cr5=21).items():
                    row[k] = f[i]
            elif t in oldmap:
                for k in ("pl","pvp","psr","dy","evebit","evebitda","mb","mebit","ml","lc","roic","roe","pla","dlpl","cr5"):
                    if k in oldmap[t]: row[k] = oldmap[t][k]
            br.append(row)
        br.sort(key=lambda r: -(r["lq"] or 0))
    # EUA
    try:
        us = nasdaq(); log.append(f"Nasdaq: {len(us)} ações")
    except Exception as e:
        us = old_us; log.append(f"Nasdaq FALHOU: {e}")
    # Histórico
    syms = [r["t"] + ".SA" for r in br[:100]] + ["^BVSP"] + [r["t"] for r in us if r["t"] != "GOOG"][:117] + ["^GSPC", "^IXIC", "BRL=X"] + FX
    hist = {}
    def one(s):
        try: return s, chart(s)
        except Exception: return s, None
    with ThreadPoolExecutor(6) as ex:
        for s, h in ex.map(one, syms):
            key = s.replace(".SA", "")
            if h: hist[key] = h
            elif key in old_h: hist[key] = old_h[key]
    log.append(f"Yahoo: {len(hist)} históricos")
    for r in br:
        h = hist.get(r["t"])
        if h and r["c"] is None and len(h["c"]) > 1: r["c"] = round((h["c"][-1] / h["c"][-2] - 1) * 100, 2)
    save("br.json", br); save("us.json", us); save("hist.json", hist)
    hx = os.path.join(SITE, "hx"); os.makedirs(hx, exist_ok=True)
    def hxsave(key, upd):
        path = os.path.join(hx, fname(key))
        try: prev = json.load(open(path))
        except Exception: prev = {}
        for k in ("d1", "maxAt"): prev.pop(k, None)
        prev.update(upd); json.dump(prev, open(path, "w"), separators=(",", ":"))
    for key, w in LONG.items(): hxsave(key, {"max": w})
    log.append(f"Yahoo histórico completo: {len(LONG)} ativos")
    time.sleep(45)   # dá um respiro ao Yahoo antes dos pedidos intradiários
    ok = 0; falhas = 0; erro1 = ""
    for sym in syms:
        try:
            d5 = intraday(sym)
        except Exception as e:
            d5 = None
            if not erro1: erro1 = f"{sym}: {e}"
        if d5:
            hxsave(sym.replace(".SA", ""), {"d5": d5}); ok += 1; falhas = 0
        else:
            falhas += 1
            if falhas >= 8: log.append("Yahoo intradiário: muitas falhas seguidas, parei"); break
        time.sleep(0.8)
    log.append(f"Yahoo intradiário: {ok} ativos" + (f" (1º erro: {erro1[:160]})" if erro1 else ""))
    # Macro
    idx = os.path.join(SITE, "index.html"); s = open(idx, encoding="utf-8").read()
    try:
        selic = float(bcb(432, 1)[-1]["valor"]); cdi = bcb(4389, 1)[-1]; i12 = bcb(13522, 1)[-1]
        usd = bcb(1, 1)[-1]; poup = float(bcb(195, 1)[-1]["valor"])
        ipm = [[x["data"][3:], float(x["valor"])] for x in bcb(433, 12)]
        mes = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"]
        d12 = i12["data"]; ip_lbl = f"12 meses até {mes[int(d12[3:5]) - 1]}/{d12[6:]}"
        macro = (f'const MACRO={{selic:{selic},selicData:"meta vigente, BCB",cdi:{float(cdi["valor"])},cdiData:"{cdi["data"]}",'
                 f'ipca12:{float(i12["valor"])},ipcaData:"{ip_lbl}",ptax:{float(usd["valor"])},ptaxData:"{usd["data"]}",poupMes:{poup},\n ipcaM:{json.dumps(ipm)}}};')
        save("macro.json", {"selic": selic, "cdi": float(cdi["valor"]), "cdiData": cdi["data"], "ipca12": float(i12["valor"]),
                            "ipcaData": ip_lbl, "ptax": float(usd["valor"]), "ptaxData": usd["data"], "poupMes": poup, "ipcaM": ipm})
        new_s, n = re.subn(r"const MACRO=\{[^;]*?\]\]\};", lambda m: macro, s, count=1)
        if n != 1: raise ValueError("bloco MACRO não encontrado no index.html")
        s = new_s
        log.append(f"BCB: Selic {selic}, CDI {cdi['valor']}, IPCA12 {i12['valor']}")
    except Exception as e:
        log.append(f"BCB FALHOU: {e}")
    try:
        save("macrohist.json", macrohist()); log.append("BCB histórico: ok")
    except Exception as e:
        log.append(f"BCB histórico FALHOU: {e}")
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3)))
    save("asof.json", {"asof": f"{now:%d/%m/%Y %H:%M}"})
    s = re.sub(r'(let|const) ASOF="[^"]*";', lambda m: f'{m.group(1)} ASOF="{now:%d/%m/%Y %H:%M}";', s, count=1)
    s = re.sub(r'\$\("#asof"\)\.textContent=`Dados de \$\{ASOF\}[^`]*`',
               '$("#asof").textContent=`Dados de ${ASOF} (horário de Brasília) · atualização automática diária · não é tempo real`', s, count=1)
    for marca in ("const PRODUTOS=[", " ASOF=", "function renderOverview", "</script>"):
        if marca not in s: raise SystemExit(f"index.html ficaria quebrado (falta {marca}); nada foi salvo")
    open(idx, "w", encoding="utf-8").write(s)
    print("\n".join(log))

if __name__ == "__main__":
    main()
