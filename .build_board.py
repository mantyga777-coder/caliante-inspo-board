#!/usr/bin/env python3
import json, os, urllib.parse, datetime, hashlib, base64, sys, subprocess, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
THUMBS = os.path.join(BASE, ".thumbs")
# Per Doppelklick gestartet kennt der Finder /opt/homebrew/bin nicht — Pfad selbst suchen.
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
SIPS = "/usr/bin/sips"          # Bilder, kann auch HEIC vom iPhone
BILD_EXT = ('.jpg','.jpeg','.png','.heic','.webp')
BILDER_ORDNER = os.path.join(BASE, "INSPO_INBOX", "bilder")
MOBIL_MAX = 20                  # so viele Bilder je Slot wandern in die Handy-Datei
THEMEN_ORDNER = os.path.join(BASE, "_Themen")  # Spiegelung der Kategorien als echte Ordner im Finder
# Was landet im Board? True = nur was in INSPO_INBOX liegt (Neuanfang),
# False = zusätzlich das vorhandene Material in den Produktionsordnern.
NUR_INBOX = True
STANDARD_CATS = ["Unboxing","UGC / Zuhause","Lifestyle-Shooting","Street","Outfitcheck","Spiegel-Slideshow","Produkt / Ästhetik","Sonstiges"]
# Themen, Notizen, Status und Ausgeblendetes liegen hier — überlebt Browserwechsel und Neubauten.
DATEN = os.path.join(BASE, "BOARD_DATEN.json")

def daten_laden():
    d = {}
    if os.path.exists(DATEN):
        try:
            d = json.load(open(DATEN, encoding='utf-8'))
        except Exception as e:
            print(f"  ! BOARD_DATEN.json unlesbar ({e}) — arbeite mit Standardwerten weiter.")
            d = {}
    d.setdefault("kategorien", list(STANDARD_CATS))
    d.setdefault("eintraege", {})
    return d

DATEN_INHALT = daten_laden()
CATS = DATEN_INHALT["kategorien"] or list(STANDARD_CATS)
NOTFALL_CAT = "Sonstiges" if "Sonstiges" in CATS else CATS[-1]

def guess(t):
    t=t.lower()
    if any(k in t for k in ["unbox","paket","auspack"]): return "Unboxing"
    if any(k in t for k in ["mirror","spiegel","slideshow","ootd"]): return "Spiegel-Slideshow"
    if any(k in t for k in ["street","strasse","city","vespa","outdoor"]): return "Street"
    if any(k in t for k in ["outfit","fitcheck","styling"]): return "Outfitcheck"
    if any(k in t for k in ["ugc","home","zuhause","selfie"]): return "UGC / Zuhause"
    if any(k in t for k in ["shoot","editorial","kampagne","lab_drop","soul","kling"]): return "Lifestyle-Shooting"
    if any(k in t for k in ["closeup","detail","flatlay","color","tee","plunge","capri","loafer","product"]): return "Produkt / Ästhetik"
    return "Sonstiges"

def thumb_b64(rel, full):
    key = hashlib.md5((rel+"\n").encode()).hexdigest()[:16]
    p = os.path.join(THUMBS, key+".jpg")
    if not os.path.exists(p):
        try:
            subprocess.run([FFMPEG,"-y","-loglevel","error","-ss","1","-i",full,"-vframes","1",
                            "-vf","scale=200:-2","-q:v","6",p], check=True)
        except Exception:
            return ""
    return "data:image/jpeg;base64," + base64.b64encode(open(p,'rb').read()).decode()

def bild_thumb(rel, full):
    key = hashlib.md5((rel+"\n").encode()).hexdigest()[:16]
    p = os.path.join(THUMBS, key+".jpg")
    if not os.path.exists(p):
        try:
            subprocess.run([SIPS,"-s","format","jpeg","-Z","200","--out",p,full],
                           check=True, capture_output=True)
        except Exception:
            return ""
    return "data:image/jpeg;base64," + base64.b64encode(open(p,'rb').read()).decode()

def bild_quelle(rel, full):
    """HEIC zeigt kein Browser an — davon eine JPEG-Ansicht ablegen, Original bleibt unberührt."""
    if not rel.lower().endswith('.heic'):
        return urllib.parse.quote(rel.replace(os.sep,'/'))
    key = hashlib.md5((rel+"|gross\n").encode()).hexdigest()[:16]
    p = os.path.join(THUMBS, key+".jpg")
    if not os.path.exists(p):
        try:
            subprocess.run([SIPS,"-s","format","jpeg","-Z","1400","--out",p,full],
                           check=True, capture_output=True)
        except Exception:
            return ""
    return urllib.parse.quote(os.path.relpath(p,BASE).replace(os.sep,'/'))

def anreichern(e):
    """Gespeichertes aus BOARD_DATEN.json auf den Eintrag legen."""
    s = DATEN_INHALT["eintraege"].get(e["id"], {})
    if s.get("ausgeblendet"): e["aus"] = True   # bleibt drin, damit es zurückholbar ist
    kats = s.get("kategorien")
    if kats is None:
        alt = s.get("kategorie")           # altes Format: eine einzelne Kategorie
        kats = [alt] if alt else [e["cat"]]
    kats = [k for k in kats if k in CATS] or [NOTFALL_CAT]   # gelöschtes Thema → Auffangkategorie
    e["cat"] = kats[0]
    e["cats"] = kats
    e["notiz"] = s.get("notiz","")
    e["status"] = s.get("status","")
    return e

entries=[]
for root,dirs,files in os.walk(os.path.join(BASE,"INSPO_INBOX") if NUR_INBOX else BASE):
    dirs[:]=[d for d in dirs if not d.startswith('.') and d not in ('claude-obsidian','node_modules','_papierkorb','_Themen')
             and not os.path.exists(os.path.join(root,d,'package.json'))]
    for f in sorted(files):
        if not f.lower().endswith(('.mp4','.mov','.webm','.m4v')): continue
        if '_superseded' in root: continue
        full=os.path.join(root,f); rel=os.path.relpath(full,BASE)
        parts=rel.split(os.sep); folder=parts[-2] if len(parts)>1 else "—"
        inbox = rel.startswith("INSPO_INBOX")
        e=anreichern({"type":"video","src":urllib.parse.quote(rel.replace(os.sep,'/')),
            "id":rel,"name":f,"folder":folder,
            "origin":"Inbox (neu)" if inbox else ("Referenz" if "refvid" in rel.lower() or rel.startswith("Referenzvideos") else "Eigenes Material"),
            "cat":guess(rel),"mb":round(os.path.getsize(full)/1048576,1),"date":"","thumb":thumb_b64(rel,full),
            "ts":os.path.getmtime(full)})
        if e: entries.append(e)

# Bilder-Slots: jeder Unterordner in INSPO_INBOX/bilder ist eine Karte zum Durchswipen.
if os.path.isdir(BILDER_ORDNER):
    for slot in sorted(os.listdir(BILDER_ORDNER)):
        ordner=os.path.join(BILDER_ORDNER,slot)
        if slot.startswith('.') or not os.path.isdir(ordner): continue
        dateien=[f for f in sorted(os.listdir(ordner)) if f.lower().endswith(BILD_EXT)]
        if not dateien: continue
        bilder=[]; gesamt=0; neuestes=0
        for f in dateien:
            full=os.path.join(ordner,f); rel=os.path.relpath(full,BASE)
            gesamt+=os.path.getsize(full); neuestes=max(neuestes,os.path.getmtime(full))
            bilder.append({"src":bild_quelle(rel,full),"thumb":bild_thumb(rel,full),"orig":rel})
        rel_slot=os.path.relpath(ordner,BASE)
        e=anreichern({"type":"bilder","id":rel_slot,"name":slot,"folder":"Bilder","src":"",
            "origin":"Inbox (neu)","cat":guess(rel_slot),"mb":round(gesamt/1048576,1),
            "date":"","thumb":bilder[0]["thumb"],"bilder":bilder,"ts":neuestes})
        if e: entries.append(e)

lp=os.path.join(BASE,"INSPO_INBOX","links.md")
if os.path.exists(lp):
    for line in open(lp,encoding='utf-8'):
        line=line.strip()
        if not line or line.startswith('#'): continue
        p=[x.strip() for x in line.split('|')]
        if len(p)<2: continue
        url=p[1]; kw=p[2] if len(p)>2 else ""
        plat="TikTok" if "tiktok" in url else ("Instagram" if "instagram" in url else "Web")
        try: ts=datetime.datetime.strptime(p[0],"%Y-%m-%d").timestamp()
        except Exception: ts=0
        e=anreichern({"type":"link","src":url,"id":url,"name":kw or url[:44],"folder":plat,
            "origin":"Inbox (neu)","cat":guess(kw+" "+url),"mb":0,"date":p[0],"thumb":"","ts":ts})
        if e: entries.append(e)

entries.sort(key=lambda e: e.get("ts",0), reverse=True)  # neuestes zuerst

def themen_ordner_bauen(sichtbar):
    """_Themen/<Kategorie>/ neu aufbauen — Verknüpfungen, damit Originale nie bewegt werden."""
    shutil.rmtree(THEMEN_ORDNER, ignore_errors=True)
    angelegt=0
    for e in sichtbar:
        if e["type"] not in ("video","bilder"): continue
        quelle=os.path.join(BASE,e["id"])
        if not os.path.exists(quelle): continue
        for cat in e["cats"]:   # bei mehreren Themen: in jedem eine eigene Verknüpfung
            ordner=os.path.join(THEMEN_ORDNER,cat)
            os.makedirs(ordner,exist_ok=True)
            stem,ext=os.path.splitext(os.path.join(ordner,os.path.basename(quelle))); i=2; ziel=stem+ext
            while os.path.lexists(ziel):
                ziel=f"{stem}-{i}{ext}"; i+=1
            os.symlink(quelle,ziel); angelegt+=1
    return angelegt

WEB_ORDNER = os.path.join(BASE, "web")   # verkleinerte Fassungen für die Team-Seite im Netz

def web_kopie(rel, full):
    """Kleine Web-Fassung anlegen (falls noch nicht da) und ihren Pfad zurückgeben.
    Inspo-Referenzen brauchen keine Master-Qualität — spart ~98% Größe."""
    ziel = os.path.join(WEB_ORDNER, rel)
    ist_bild = rel.lower().endswith(BILD_EXT)
    # Endung vor der Existenzprüfung festlegen: Bilder werden immer .jpg (klein). Sonst prüft
    # der Mac case-insensitiv gegen ".JPG", liefert den Pfad in Großschreibung zurück — und der
    # Server von GitHub unterscheidet Groß-/Kleinschreibung sehr wohl und antwortet mit 404.
    if ist_bild:
        ziel = os.path.splitext(ziel)[0] + ".jpg"
    if os.path.exists(ziel) and os.path.getmtime(ziel) >= os.path.getmtime(full):
        return urllib.parse.quote(os.path.relpath(ziel, BASE).replace(os.sep,'/'))
    os.makedirs(os.path.dirname(ziel), exist_ok=True)
    try:
        if ist_bild:
            subprocess.run([SIPS,"-s","format","jpeg","-Z","1400","--out",ziel,full],
                           check=True, capture_output=True)
        else:
            subprocess.run([FFMPEG,"-y","-loglevel","error","-i",full,
                            "-vf","scale=-2:720","-c:v","libx264","-crf","28","-preset","fast",
                            "-c:a","aac","-b:a","96k","-movflags","+faststart",ziel], check=True)
    except Exception as fehler:
        print(f"  ! Web-Fassung fehlgeschlagen für {rel}: {fehler}")
        return ""
    return urllib.parse.quote(os.path.relpath(ziel, BASE).replace(os.sep,'/'))

origins=["Inbox (neu)","Referenz","Eigenes Material"]

gekappt=0
def build(mobile, web=False):
    global gekappt
    data=[]
    for e in entries:
        if web and e.get("aus"): continue   # Ausgeblendetes gehört nicht in die Team-Fassung
        d=dict(e); d.pop("ts",None)
        if web:
            # Team-Seite: auf die verkleinerten Web-Fassungen zeigen, nicht auf lokale Pfade.
            if e["type"]=="video":
                d["src"]=web_kopie(e["id"], os.path.join(BASE,e["id"]))
            elif e["type"]=="bilder":
                d["bilder"]=[{"src":web_kopie(b["orig"], os.path.join(BASE,b["orig"])),
                              "thumb":b["thumb"]} for b in e["bilder"]]
        if mobile and e["type"]=="video": d.pop("src",None)
        if mobile and e["type"]=="bilder":
            # Handy-Datei trägt alles in sich — darum nur die Vorschaubilder und nicht endlos viele.
            if len(d["bilder"])>MOBIL_MAX: gekappt+=len(d["bilder"])-MOBIL_MAX
            d["bilder"]=[{"thumb":b["thumb"]} for b in d["bilder"][:MOBIL_MAX]]
        data.append(d)
    tpl=open(os.path.join(BASE,".board_template.html"),encoding='utf-8').read()
    out=tpl.replace("__DATA__",json.dumps(data,ensure_ascii=False))
    out=out.replace("__CATS__",json.dumps(CATS,ensure_ascii=False))
    out=out.replace("__ORIGCHIPS__","".join(f'<span class="chip of" data-o="{o}">{o}</span>' for o in origins))
    out=out.replace("__N__",str(sum(1 for e in entries if not e.get("aus"))))
    out=out.replace("__DATE__",datetime.date.today().strftime("%d.%m.%Y"))
    out=out.replace("__MOBILE__","true" if mobile else "false")
    out=out.replace("__NURLESEN__","true" if web else "false")
    name="index.html" if web else ("CALIANTE_BOARD_HANDY.html" if mobile else "CALIANTE_VIDEO_BOARD.html")
    open(os.path.join(BASE,name),"w",encoding='utf-8').write(out)
    ICLOUD="/sessions/tender-dazzling-sagan/mnt/com~apple~CloudDocs/CALIANTE"
    if mobile and os.path.isdir(ICLOUD):
        open(os.path.join(ICLOUD,"CALIANTE_BOARD.html"),"w",encoding='utf-8').write(out)
    return name, len(out)

for m in (False,True):
    n,s=build(m); print(f"{n}: {s/1024:.0f} KB")
if "--web" in sys.argv:   # zusätzlich die Fassung fürs Team im Netz, mit verkleinerten Videos
    print("Web-Fassungen werden erzeugt (einmalig je Datei, danach schnell) …")
    n,s=build(False, web=True); print(f"{n}: {s/1024:.0f} KB")
sichtbar=[e for e in entries if not e.get("aus")]
slots=[e for e in sichtbar if e["type"]=="bilder"]
themen_n=themen_ordner_bauen(sichtbar)
print(f"{len(sichtbar)} Einträge, {sum(1 for e in sichtbar if e['thumb'])} mit Vorschaubild"
      + (f", {len(entries)-len(sichtbar)} ausgeblendet" if len(sichtbar)!=len(entries) else "")
      + f" · {len(CATS)} Themen"
      + (f" · {len(slots)} Bilder-Slots mit {sum(len(e['bilder']) for e in slots)} Bildern" if slots else ""))
print(f"_Themen/: {themen_n} Verknüpfungen nach Kategorie sortiert")
if gekappt:
    print(f"  Hinweis: In der Handy-Datei fehlen {gekappt} Bilder — je Slot sind dort {MOBIL_MAX} enthalten.")
