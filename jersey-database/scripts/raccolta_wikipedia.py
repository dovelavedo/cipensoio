#!/usr/bin/env python3
"""Raccoglie da Wikipedia in italiano i dati di una stagione di Serie A.

Uso:  python3 scripts/raccolta_wikipedia.py 1997-1998

Produce:
  data/serie-a-<stagione>.json          dati pronti da caricare nel database
  data/DA-VERIFICARE-<stagione>.md      elenco di ciò che manca o è incerto

Ogni dato porta con sé la pagina di provenienza e nasce "da verificare".
Testi di Wikipedia: licenza CC BY-SA 4.0. Non vengono scaricate immagini.
"""
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

UA = "JerseyDatabaseBot/0.1 (archivio storico maglie; raccolta dati a bassa frequenza)"
QUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(QUI, "..", ".cache-wikipedia")
DATA = os.path.join(QUI, "..", "data")
PRIMA_STAGIONE_CON_NUMERI_FISSI = 1995  # 1995-96


def wikitesto(titolo):
    """Scarica il testo sorgente di una pagina (con copia locale per non ripetere le richieste)."""
    os.makedirs(CACHE, exist_ok=True)
    f = os.path.join(CACHE, titolo.replace(" ", "_").replace("/", "_") + ".txt")
    if os.path.exists(f):
        return open(f, encoding="utf-8").read()
    url = "https://it.wikipedia.org/w/api.php?" + urllib.parse.urlencode(dict(
        action="parse", page=titolo, prop="wikitext", format="json", formatversion=2, redirects=1, maxlag=5))
    for tentativo in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            testo = json.load(urllib.request.urlopen(req))["parse"]["wikitext"]
            open(f, "w", encoding="utf-8").write(testo)
            time.sleep(2)
            return testo
        except urllib.error.HTTPError as e:
            time.sleep(min(int(e.headers.get("Retry-After") or 5 * (tentativo + 1)), 60))
    raise SystemExit("Impossibile scaricare: " + titolo)


def url_pagina(titolo):
    return "https://it.wikipedia.org/wiki/" + urllib.parse.quote(titolo.replace(" ", "_"))


def sezione(w, nome):
    m = re.search(r"^(=+)\s*" + nome + r".*?=+\s*$", w, re.M | re.I)
    if not m:
        return ""
    livello = len(m.group(1))
    fine = re.search(r"^={2,%d}[^=]" % livello, w[m.end():], re.M)
    return w[m.end():m.end() + fine.start()] if fine else w[m.end():]


def pulisci(s):
    s = re.sub(r"<ref[^>]*/>", "", s)
    s = re.sub(r"<ref.*?</ref>", "", s, flags=re.S)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    return s.replace("'", "").strip() if s.count("'") >= 4 else s.strip()


def senza_ref(s):
    s = re.sub(r"<ref[^>]*/>", "", s)
    return re.sub(r"<ref.*?</ref>", "", s, flags=re.S)


# ---------- campionato ----------

def squadre_e_classifica(w):
    pagine = {}
    for nome, pagina in re.findall(r"\{\{[Cc]alcio ([^|}]+)[^}]*\}\}\s*\n\|\s*''\[\[([^|\]]+)\|dettagli\]\]''", w):
        pagine[nome.strip()] = pagina
    classifica = {}
    for pos, nome in re.findall(r"\|\|\s*(\d+)\.\s*\|\|[^\n]*?\{\{[Cc]alcio ([^|}]+)", sezione(w, "Classifica finale")):
        classifica[nome.strip()] = int(pos)
    return pagine, classifica


# ---------- maglie e sponsor ----------

TIPI = [(r"portiere", None), (r"casa|1ª divisa|prima", "home"), (r"trasferta|2ª divisa|seconda", "away"),
        (r"terza|3ª divisa", "third"), (r"quarta|4ª divisa", "fourth")]


def maglie(w):
    out = []
    for blocco in re.findall(r"\{\{Divisa calcio(.*?)\n\}\}", sezione(w, "Divise e sponsor"), flags=re.S | re.I):
        t = re.search(r"\|\s*title\s*=\s*(.*)", blocco)
        titolo = pulisci(t.group(1)) if t else ""
        tipo = "special"
        for schema, valore in TIPI:
            if re.search(schema, titolo, re.I):
                tipo = valore
                break
        if tipo:
            out.append({"tipo": tipo, "nome_originale": titolo})
    return out


def nome_dopo(testo):
    """Primo nome di azienda citato nel pezzo di frase: un link [[...]] oppure una parola con la maiuscola."""
    m = re.search(r"\[\[([^\]]+)\]\]", testo)
    semplice = re.search(r"(?:è|fu|era|furono)\s+([A-Z][\w&.\- ]*?)(?=[.,;<\n]|$)", testo)
    if m and (not semplice or m.start() < semplice.start()):
        return m.group(1).split("|")[-1].strip()
    return semplice.group(1).strip() if semplice else None


def sponsor(w):
    testo = senza_ref(re.sub(r"\{\{Divisa calcio.*?\n\}\}", "", sezione(w, "Divise e sponsor"), flags=re.S | re.I))
    tecnico = re.search(r"sponsor tecnico|fornitor\w+(?: ufficiale)?(?: di materiale)? tecnico|materiale tecnico", testo, re.I)
    main = re.search(r"sponsor ufficiale|sponsor principale|main sponsor", testo, re.I)
    ris = {"tecnico": None, "main": None, "testo": re.sub(r"\s+", " ", re.sub(r"\[\[File:[^\n]*\n", "", testo)).strip(" |-{}")[:700]}
    punti = sorted([m.start() for m in (tecnico, main) if m]) + [len(testo)]
    for chiave, m in (("tecnico", tecnico), ("main", main)):
        if m:
            fine = punti[punti.index(m.start()) + 1]
            frase = testo[m.end():fine]
            ris[chiave] = nome_dopo(frase.split(". ")[0])
    if re.search(r"non presenta(?:va)? sponsor|senza sponsor", testo, re.I):
        ris["senza_main_sponsor"] = True
    return ris


# ---------- rosa e statistiche ----------

def rosa(w, con_numeri):
    out = []
    for linea in re.findall(r"^\{\{Calciatore in rosa\|.*$", sezione(w, "Rosa"), flags=re.M):
        # le note (es. "ceduto a gennaio") stanno in <ref>: le metto da parte e le tolgo dalla riga
        note = [pulisci(n) for n in re.findall(r"<ref[^>/]*>(.*?)</ref>", linea)]
        richiami = re.findall(r"<ref\s+name\s*=\s*\"?([^\">/]+)\"?\s*/>", linea)
        corsivo = "nome=''" in linea.replace(" ", "")
        riga = senza_ref(linea)
        riga = riga[len("{{Calciatore in rosa|"):riga.rindex("}}")]
        campi = dict(re.findall(r"(?:^|\|)\s*(n|nazione|nome|ruolo)\s*=\s*((?:\[\[[^\]]*\]\]|[^|])*)", riga))
        nome_grezzo = campi.get("nome", "")
        nome = pulisci(nome_grezzo).strip("' ")
        if not nome:
            continue
        link = re.search(r"\[\[([^|\]]+)", nome_grezzo)
        for r in richiami:
            d = re.search(r"<ref\s+name\s*=\s*\"?%s\"?\s*>(.*?)</ref>" % re.escape(r.strip()), w, flags=re.S)
            if d:
                note.append(pulisci(d.group(1)))
        numero = re.sub(r"\D", "", campi.get("n", ""))
        out.append({
            "nome": nome,
            "pagina_wikipedia": link.group(1) if link else None,
            "numero": int(numero) if (numero and con_numeri) else None,
            "ruolo": {"P": "portiere", "D": "difensore", "C": "centrocampista", "A": "attaccante"}.get(campi.get("ruolo", "").strip()),
            "nazione": campi.get("nazione", "").strip() or None,
            "partito_a_stagione_in_corso": corsivo,
            "nota": "; ".join(dict.fromkeys(n for n in note if n and "cita" not in n.lower())) or None,
            "presenze": None, "gol": None,
        })
    return out


def chiave(nome):
    import unicodedata
    n = unicodedata.normalize("NFD", nome.lower())
    return re.sub(r"[^a-z ]", "", "".join(c for c in n if unicodedata.category(c) != "Mn")).strip()


def statistiche(w):
    """Presenze e gol in campionato. Per i portieri Wikipedia indica i gol subiti con il segno meno."""
    s = sezione(w, "Statistiche dei giocatori")
    comp = re.search(r"Competizione1\s*=\s*(.*)", s)
    if not s or not comp or "Serie A" not in comp.group(1):
        return None
    out = {}
    for sort, numeri in re.findall(r"\{\{Sortname\|([^}]*)\}\}'*\s*(?:<ref.*?(?:</ref>|/>))*\s*\{\{Sommastat\s*\|([^}]*)\}\}", s):
        parti = [p.strip().strip("'") for p in sort.split("|")]
        nolink = [p for p in parti if p.startswith("nolink")]
        nome = pulisci(nolink[0].split("=", 1)[1]) if nolink and "=" in nolink[0] and len(nolink[0]) > 9 else (
            parti[2] if len(parti) > 2 and "=" not in parti[2] else parti[1])
        nome = re.sub(r"\s*\(.*?\)", "", nome)
        valori = [v.strip() for v in numeri.split("|") if "=" not in v and v.strip()]
        try:
            # il trattino significa "mai sceso in campo in questa competizione"
            pres, gol = (0 if v in "-–" else int(v) for v in valori[:2])
            out[chiave(nome)] = (nome, pulisci(parti[1]), pres, gol)
        except ValueError:
            pass
    return out


def unisci(giocatori, stat, mancanti):
    usate = set()
    for g in giocatori:
        k = chiave(g["nome"])
        trovata = k if k in stat else next((s for s in stat if s not in usate and chiave(stat[s][1]) and k.endswith(chiave(stat[s][1])) and s[:1] == k[:1]), None)
        if trovata:
            usate.add(trovata)
            _, _, pres, gol = stat[trovata]
            g["presenze"] = pres
            if gol < 0:
                g["gol"], g["gol_subiti"] = 0, -gol
            else:
                g["gol"] = gol
        else:
            mancanti.append("presenze/gol non trovati per **%s**" % g["nome"])
    for k, (nome, _, pres, gol) in stat.items():
        if k not in usate:
            giocatori.append({"nome": nome, "pagina_wikipedia": None, "numero": None, "ruolo": None, "nazione": None,
                              "partito_a_stagione_in_corso": False, "nota": "Presente nelle statistiche ma non nell'elenco della rosa",
                              "presenze": pres, "gol": max(gol, 0)})
            mancanti.append("**%s** compare nelle statistiche ma non nella rosa: numero e ruolo da inserire" % nome)


# ---------- programma ----------

def main(stagione):
    anno = int(stagione[:4])
    con_numeri = anno >= PRIMA_STAGIONE_CON_NUMERI_FISSI
    pagina_campionato = "Serie A " + stagione
    pagine, classifica = squadre_e_classifica(wikitesto(pagina_campionato))
    risultato = {"nazione": "Italia", "competizione": "Serie A", "stagione": stagione,
                 "fonte": url_pagina(pagina_campionato), "licenza_fonte": "CC BY-SA 4.0",
                 "stato": "da_verificare", "squadre": []}
    report = ["# Da verificare - Serie A %s" % stagione, "",
              "Tutti i dati vengono da Wikipedia in italiano e sono segnati \"da verificare\".",
              "Qui sotto solo ciò che **manca** o è **incerto**. Nulla è stato inventato.", ""]
    for nome in sorted(pagine):
        w = wikitesto(pagine[nome])
        problemi = []
        kit, sp = maglie(w), sponsor(w)
        giocatori = rosa(w, con_numeri)
        stat = statistiche(w)
        if not kit:
            problemi.append("**maglie non elencate** su Wikipedia: da inserire a mano")
        elif not {"home", "away"} <= {k["tipo"] for k in kit}:
            problemi.append("elenco maglie incompleto (manca home o away)")
        for k in kit:
            if k["tipo"] == "special":
                problemi.append("maglia speciale \"%s\": controllare che sia stata usata in gara" % k["nome_originale"])
        if not sp["tecnico"]:
            problemi.append("**sponsor tecnico** non trovato")
        if not sp["main"]:
            problemi.append("**main sponsor** non trovato" + (" (il testo dice che la maglia era senza sponsor)" if sp.get("senza_main_sponsor") else ""))
        problemi.append("sponsor secondari: Wikipedia non li riporta, da controllare")
        if not giocatori:
            problemi.append("**rosa non trovata**")
        if con_numeri and any(g["numero"] is None for g in giocatori):
            problemi.append("giocatori senza numero: " + ", ".join(g["nome"] for g in giocatori if g["numero"] is None))
        if stat is None:
            problemi.append("**presenze e gol non disponibili** su Wikipedia per questa squadra")
        else:
            unisci(giocatori, stat, problemi)
        if nome not in classifica:
            problemi.append("**piazzamento** non trovato")
        risultato["squadre"].append({
            "nome": nome, "piazzamento": classifica.get(nome), "fonte": url_pagina(pagine[nome]),
            "sponsor_tecnico": sp["tecnico"], "main_sponsor": sp["main"], "sponsor_secondari": [],
            "testo_fonte_sponsor": sp["testo"], "maglie": kit, "rosa": giocatori, "stato": "da_verificare"})
        report += ["## %s" % nome, "Fonte: %s" % url_pagina(pagine[nome]), ""] + ["- " + p for p in problemi] + [""]
    os.makedirs(DATA, exist_ok=True)
    json.dump(risultato, open(os.path.join(DATA, "serie-a-%s.json" % stagione), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    open(os.path.join(DATA, "DA-VERIFICARE-%s.md" % stagione), "w", encoding="utf-8").write("\n".join(report))
    for s in risultato["squadre"]:
        print("%2s %-11s tecnico=%-10s main=%-22s maglie=%-28s rosa=%2d con_presenze=%2d" % (
            s["piazzamento"], s["nome"], s["sponsor_tecnico"], s["main_sponsor"],
            ",".join(k["tipo"] for k in s["maglie"]), len(s["rosa"]), sum(g["presenze"] is not None for g in s["rosa"])))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1997-1998")
