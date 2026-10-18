#!/usr/bin/env python3
"""Build the Marymoor Park BirdNET sightings report from a detections export.

Usage:
  python3 -I build_report.py detections-<from>-to-<to>.json --out report.html [options]

Input is the station's detections export (see references/export-format.md):
  {"exportedAt", "model", "since", "until", "minConfidence", "sort", "order",
   "total", "detections": [{"id", "audioFileId", "startSec", "endSec",
   "detectedAt", "scientificName", "commonName", "confidence",
   "clip": {"startSec", "endSec"}, "reviewStatus", "model", "reference",
   "stationName", "night"}, ...]}

Writes the HTML page plus <out>.summary.json (every number the page shows) and
<out>.clips.json (the audioFileIds whose recordings the page wants to play).
With --audio-dir, matching recordings are copied to a clips/ folder next to the
page. Owl photos are fetched from the iNaturalist API (network needed; cached in
.owl-photos/ next to the page). Standard library only.
"""
import argparse
import base64
import datetime as dt
import html
import json
import math
import re
import shutil
import urllib.parse
import urllib.request
import sys
from collections import Counter, defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir
from style import CSS, OWL_SVG  # noqa: E402

MARYMOOR_LAT, MARYMOOR_LON = 47.6613, -122.1180
TZ = ZoneInfo("America/Los_Angeles")
HIGH, MEDIUM = 0.85, 0.70
DETECTION_URL = "https://owls.eastsideaudubon.org/app/detections/{reference}/{id}"
# Friendly names for recording stations, keyed by the station code at the end of
# the export's `reference` (e.g. OWL-20261016-SR01 -> SR01).
STATION_NAMES = {"SR01": "Marymoor Park Station"}

# Owl photos: research-grade iNaturalist observations near Marymoor with a CC licence.
INAT_API = "https://api.inaturalist.org/v1/observations"
PHOTO_LICENSES = ["cc0", "cc-by", "cc-by-sa", "cc-by-nc", "cc-by-nc-sa"]
LICENSE_URL = {"cc0": "https://creativecommons.org/publicdomain/zero/1.0/",
               "cc-by": "https://creativecommons.org/licenses/by/4.0/",
               "cc-by-sa": "https://creativecommons.org/licenses/by-sa/4.0/",
               "cc-by-nc": "https://creativecommons.org/licenses/by-nc/4.0/",
               "cc-by-nc-sa": "https://creativecommons.org/licenses/by-nc-sa/4.0/"}
AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".webm"}

REQUIRED = ["id", "detectedAt", "scientificName", "commonName", "confidence"]
REJECTED = {"rejected", "false_positive", "falsepositive", "invalid", "incorrect", "discarded"}
VERIFIED = {"confirmed", "verified", "approved", "accepted", "correct", "reviewed"}

# Strigidae + Tytonidae genera.
OWL_GENERA = {
    "Tyto", "Phodilus", "Otus", "Megascops", "Psiloscops", "Bubo", "Strix",
    "Ciccaba", "Lophostrix", "Pulsatrix", "Glaucidium", "Micrathene", "Athene",
    "Aegolius", "Asio", "Surnia", "Ninox", "Pseudoscops", "Scotopelia",
    "Ketupa", "Nesasio", "Gymnasio", "Mimizuku",
}
EXPECTED_OWLS = {"Strix varia", "Bubo virginianus", "Tyto alba", "Tyto furcata",
                 "Megascops kennicottii", "Aegolius acadicus", "Asio flammeus"}
RARE_OWLS = {"Asio otus", "Glaucidium gnoma", "Glaucidium californicum", "Bubo scandiacus"}

NON_BIRD = re.compile(r"^(human|dog|engine|environmental|fireworks|gun|noise|power tools|"
                      r"siren|vehicle|wind|rain)\b", re.I)

EXTRA_CSS = """
.p-ok{color:var(--high);background:var(--high-bg);border:1px solid var(--high)}
.listen{display:inline-block;font-size:13px;font-weight:600;color:var(--link);padding:2px 8px;border:1px solid var(--border);border-radius:4px;white-space:nowrap}
.listen:hover{background:var(--hover);text-decoration:none}
.detid{font-size:11px;color:var(--faint);font-family:ui-monospace,Menlo,monospace}
.tm{white-space:nowrap}
.owlfig{display:flex;gap:16px;align-items:flex-start;margin:12px 0 8px;padding:0}
.owlfig img{width:120px;max-width:30%;height:auto;border-radius:6px;border:1px solid var(--border)}
.owlfig figcaption{font-size:13px;color:var(--muted);line-height:1.5}
.stats{grid-template-columns:repeat(4,1fr)}
@media (max-width:720px){.owlfig{flex-direction:column}.owlfig img{max-width:50%;width:50%}}
.themebar{background:var(--navy);display:flex;justify-content:flex-end;padding:10px 40px 0}
.themebar [role=group]{display:inline-flex;border:1px solid rgba(255,255,255,.35);border-radius:999px;overflow:hidden}
.themebar button{font:inherit;font-size:13px;color:rgba(255,255,255,.8);background:transparent;border:0;padding:4px 12px;cursor:pointer}
.themebar button[aria-pressed=true]{background:rgba(255,255,255,.2);color:#fff;font-weight:600}
.themebar button:focus-visible{outline:2px solid var(--sky);outline-offset:-2px}
.mast{padding-top:20px}
@media (max-width:720px){.themebar{padding:10px 16px 0}}
.covday{margin:0 0 18px}
.covhead{display:flex;flex-wrap:wrap;gap:4px 12px;align-items:baseline;margin-bottom:6px}
.covhead .hs-name{font-size:16px}
.covhead .hs-stats{font-size:13px}
.covbar{display:grid;grid-template-columns:repeat(96,1fr);gap:1px;height:48px;border-bottom:2px solid var(--heading)}
.cb{position:relative;display:block;height:100%}
.cb.dk{background:var(--cov-shade)}
.cb::after{content:"";position:absolute;left:0;right:0;bottom:0;height:var(--h)}
.cb.rd::after{background:var(--cov-day)}
.cb.rn::after{background:var(--cov-night)}
.cb.nr::after{height:0;bottom:3px;border-bottom:2px dotted var(--faint)}
.cb.ow::before{content:"";position:absolute;left:50%;top:2px;width:5px;height:5px;margin-left:-2.5px;border-radius:50%;background:var(--cov-owl)}
.covaxis{display:flex;justify-content:space-between;font-size:11px;color:var(--faint);margin-top:3px}
.legend .lg{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:var(--muted)}
.sw{display:inline-block;width:12px;height:12px;border-radius:2px}
.sw-day{background:var(--cov-day)}.sw-night{background:var(--cov-night)}.sw-shade{background:var(--cov-shade)}
.sw-none{height:0;border-bottom:2px dashed var(--faint)}.sw-owl{width:8px;height:8px;border-radius:50%;background:var(--cov-owl)}
:root{--cov-day:#0068a6;--cov-night:#1a375f;--cov-shade:#e3e7ed;--cov-owl:#c77d12}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--cov-day:#4fa9e0;--cov-night:#a9b8ff;--cov-shade:#243244;--cov-owl:#f2b35a}}
:root[data-theme="dark"]{--cov-day:#4fa9e0;--cov-night:#a9b8ff;--cov-shade:#243244;--cov-owl:#f2b35a}
.meta{font-size:13px;color:rgba(255,255,255,.6);margin-top:6px}
.logo{height:110px;width:auto;flex:none}
@media (max-width:720px){.logo{height:72px}}
"""


# Light / dark / auto switch. Remembers the reader's choice where storage is allowed.
THEME_JS = """<script>
(function(){
  var root=document.documentElement, btns=document.querySelectorAll('.themebar button');
  function apply(t){
    if(t==='light'||t==='dark'){root.setAttribute('data-theme',t);}else{root.removeAttribute('data-theme');t='auto';}
    btns.forEach(function(b){b.setAttribute('aria-pressed', String(b.dataset.t===t));});
  }
  var saved='auto'; try{saved=localStorage.getItem('eas-report-theme')||'auto';}catch(e){}
  apply(saved);
  btns.forEach(function(b){b.addEventListener('click',function(){
    apply(b.dataset.t); try{localStorage.setItem('eas-report-theme',b.dataset.t);}catch(e){}
  });});
})();
</script>"""


# ---------------------------------------------------------------- parsing

def parse_ts(s):
    """ISO timestamp with Z and up to nanosecond precision -> aware datetime."""
    s = str(s).strip().replace("Z", "+00:00")
    s = re.sub(r"(\.\d{6})\d+", r"\1", s)
    d = dt.datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def load(path):
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Not valid JSON: {e}")
    if not isinstance(doc, dict) or not isinstance(doc.get("detections"), list):
        raise SystemExit("Expected an object with a 'detections' list "
                         "(see references/export-format.md).")
    return doc


# ---------------------------------------------------------------- sun

def sun_times(day, lat=MARYMOOR_LAT, lon=MARYMOOR_LON, zenith=90.833):
    """NOAA approximation -> (sunrise, sunset) as local aware datetimes.
    zenith 90.833 is sunrise/sunset; 96 is civil dawn/dusk."""
    g = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)
    eqt = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                    - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    latr = math.radians(lat)
    cos_ha = (math.cos(math.radians(zenith)) / (math.cos(latr) * math.cos(decl))
              - math.tan(latr) * math.tan(decl))
    ha = math.degrees(math.acos(max(-1.0, min(1.0, cos_ha))))
    midnight = dt.datetime(day.year, day.month, day.day, tzinfo=dt.timezone.utc)
    rise = midnight + dt.timedelta(minutes=720 - 4 * (lon + ha) - eqt)
    sets = midnight + dt.timedelta(minutes=720 - 4 * (lon - ha) - eqt)
    return rise.astimezone(TZ), sets.astimezone(TZ)


_sun = {}


def sun_for(day):
    if day not in _sun:
        _sun[day] = sun_times(day)
    return _sun[day]


_civil = {}


def civil_for(day):
    """(civil dawn, civil dusk) for a local date."""
    if day not in _civil:
        _civil[day] = sun_times(day, zenith=96.0)
    return _civil[day]


def is_dark(when):
    rise, sets = sun_for(when.date())
    return when < rise or when >= sets


# ---------------------------------------------------------------- helpers

def band(c):
    return "high" if c >= HIGH else "med" if c >= MEDIUM else "low"


BAND_LABEL = {"high": "High", "med": "Medium", "low": "Low"}


def is_owl(sci, com):
    if sci and sci.split()[0] in OWL_GENERA:
        return True
    return bool(re.search(r"\bowl\b|screech-owl|pygmy-owl|saw-whet", com or "", re.I))


def owl_status(sci):
    return "expected" if sci in EXPECTED_OWLS else "rare" if sci in RARE_OWLS else "review"


def esc(s):
    return html.escape("" if s is None else str(s), quote=True)


def md(d):
    return f"{d:%b} {d.day}"


def fmt_date(d):
    return f"{d:%a} {md(d)}, {d.year}"


def fmt_time(t):
    """Clock time without seconds, labelled Pacific Time."""
    return t.strftime("%I:%M %p").lstrip("0") + " PT"


fmt_hm = fmt_time


def pill(kind, text):
    return f'<span class="pill p-{kind}">{esc(text)}</span>'


def conf_cell(c):
    return f'<span class="conf">{c*100:.1f}%</span> {pill(band(c), BAND_LABEL[band(c)])}'


def review_pill(status):
    s = (status or "").lower()
    if s in VERIFIED:
        return " " + pill("ok", "Verified")
    return ""


def dn_pill(d):
    return pill("night", "Night") if d["dark"] else pill("day", "Day")


def station_code(reference):
    m = re.search(r"([A-Za-z]+)-?(\d+)$", reference or "")
    return f"{m.group(1).upper()}{m.group(2)}" if m else None


def station_label(reference, names):
    code = station_code(reference)
    if code and code in names:
        return names[code]
    return reference or "Marymoor Park"


def pretty_code(code):
    m = re.match(r"([A-Z]+)(\d+)$", code or "")
    return f"{m.group(1)}-{m.group(2)}" if m else code


# ---------------------------------------------------------------- owl photos

def _get_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "marymoor-birdnet-report/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _get_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": "marymoor-birdnet-report/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


GENERIC_PLACE = re.compile(r"^\s*(washington|wa|king county|united states|us)\b[ ,a-z-]*$", re.I)


def owl_photo(sci, cache_dir, override=None):
    """Pick a CC-licensed, research-grade iNaturalist photo of exactly this species,
    taken within 40 km of Marymoor. Returns a dict, or None (with the reason printed)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = re.sub(r"\W+", "_", sci) + (f"_{override}" if override else "")
    meta_f, img_f = cache_dir / f"{key}.json", cache_dir / f"{key}.jpg"
    if meta_f.exists() and img_f.exists() and "author_url" in json.loads(meta_f.read_text()):
        meta = json.loads(meta_f.read_text())
        meta["data_uri"] = "data:image/jpeg;base64," + base64.b64encode(img_f.read_bytes()).decode()
        return meta
    try:
        if override:
            results = _get_json(f"{INAT_API}/{override}")["results"]
        else:
            q = urllib.parse.urlencode({
                "taxon_name": sci, "quality_grade": "research", "photos": "true",
                "photo_license": ",".join(PHOTO_LICENSES), "lat": MARYMOOR_LAT, "lng": MARYMOOR_LON,
                "radius": 40, "order_by": "votes", "per_page": 30})
            results = _get_json(f"{INAT_API}?{q}")["results"]
    except Exception as e:  # network down, API change
        print(f"WARNING: owl photo lookup failed for {sci}: {e}", file=sys.stderr)
        return None
    cands = []
    for o in results:
        t = o.get("taxon") or {}
        if t.get("name") != sci or t.get("rank") != "species":
            continue  # exact species only
        for ph in o.get("photos") or []:
            if ph.get("license_code") in PHOTO_LICENSES:
                cands.append((o, ph))
                break
    if not cands:
        print(f"WARNING: no CC-licensed research-grade photo of {sci} found near Marymoor", file=sys.stderr)
        return None
    # Prefer a named local place (a park or city) over "Washington, US", then most-faved.
    cands.sort(key=lambda c: (bool(GENERIC_PLACE.match(c[0].get("place_guess") or "")),
                              -(c[0].get("faves_count") or 0)))
    o, ph = cands[0]
    try:
        img = _get_bytes(re.sub(r"/square\.", "/medium.", ph["url"]))
    except Exception as e:
        print(f"WARNING: owl photo download failed for {sci}: {e}", file=sys.stderr)
        return None
    obs_on = o.get("observed_on") or ""
    user = o.get("user") or {}
    login = user.get("login") or ""
    meta = {
        "author": user.get("name") or login,
        "author_url": f"https://www.inaturalist.org/people/{login}" if login else "",
        "photo_page": f"https://www.inaturalist.org/photos/{ph['id']}" if ph.get("id") else "",
        "sci": sci, "observation": o["id"], "url": f"https://www.inaturalist.org/observations/{o['id']}",
        "attribution": ph.get("attribution", ""), "license": ph["license_code"],
        "license_url": LICENSE_URL.get(ph["license_code"], ""),
        "place": o.get("place_guess") or "", "observed_on": obs_on,
    }
    img_f.write_bytes(img)
    meta_f.write_text(json.dumps(meta, indent=2))
    meta["data_uri"] = "data:image/jpeg;base64," + base64.b64encode(img).decode()
    return meta


# Licence names as iNaturalist states them (its API gives no version); the link goes to
# the current 4.0 deed.
LICENSE_NAME = {"cc0": "CC0", "cc-by": "CC BY", "cc-by-sa": "CC BY-SA",
                "cc-by-nc": "CC BY-NC", "cc-by-nc-sa": "CC BY-NC-SA"}


def photo_figure(meta, com):
    """Caption follows the Creative Commons TASL pattern: Title, Author, Source, Licence."""
    lic = LICENSE_NAME.get(meta["license"], meta["license"].upper())
    who = meta.get("author") or re.sub(r"^\(c\)\s*|,?\s*(some|all|no) rights reserved.*$", "",
                                       meta.get("attribution") or "", flags=re.I).strip() or "iNaturalist user"
    who_html = (f"<a href='{esc(meta['author_url'])}'>{esc(who)}</a>" if meta.get("author_url") else esc(who))
    src = meta.get("photo_page") or meta["url"]
    when = ""
    if meta.get("observed_on"):
        d = dt.date.fromisoformat(meta["observed_on"][:10])
        when = f", {d:%B} {d.year}"
    place = re.sub(r",?\s*(USA?|United States)$", "", meta.get("place") or "")
    place = re.sub(r"\s+\d{5}(-\d{4})?\b", "", place).strip(", ")
    lic_html = f"<a href='{esc(meta['license_url'])}'>{esc(lic)}</a>" if meta.get("license_url") else esc(lic)
    return (f"<figure class='owlfig'><img src='{meta['data_uri']}' alt='{esc(com)}, photo by {esc(who)}' loading='lazy'>"
            f"<figcaption>{esc(com)}{', ' + esc(place) if place else ''}{esc(when)}.<br>"
            f"<span class='credit'>“<a href='{esc(src)}'>{esc(com)}</a>” by {who_html}, "
            f"via <a href='{esc(meta['url'])}'>iNaturalist observation {esc(meta['observation'])}</a>, "
            f"licensed under {lic_html}.</span><br>"
            f"Illustrative photo, not from this recording.</figcaption></figure>")


# ---------------------------------------------------------------- normalise

def normalise(doc):
    dets, skipped, problems = [], Counter(), Counter()
    for r in doc["detections"]:
        missing = [k for k in REQUIRED if r.get(k) in (None, "")]
        if missing:
            problems["missing " + ",".join(missing)] += 1
            continue
        com, sci = str(r["commonName"]).strip(), str(r["scientificName"]).strip()
        if NON_BIRD.match(com) or NON_BIRD.match(sci):
            skipped[f"non-bird: {com}"] += 1
            continue
        status = str(r.get("reviewStatus") or "unreviewed")
        if status.lower() in REJECTED:
            skipped[f"reviewStatus {status}"] += 1
            continue
        try:
            when = parse_ts(r["detectedAt"]).astimezone(TZ)
            conf = float(r["confidence"])
        except (TypeError, ValueError):
            problems["unparseable time/confidence"] += 1
            continue
        if conf > 1:
            conf /= 100.0
        clip = r.get("clip") if isinstance(r.get("clip"), dict) else {}
        cs = clip.get("startSec", r.get("startSec"))
        ce = clip.get("endSec", r.get("endSec"))
        dets.append({
            "id": r["id"], "com": com, "sci": sci, "conf": conf, "when": when,
            "date": when.date(), "dark": is_dark(when), "owl": is_owl(sci, com),
            "audio": r.get("audioFileId"), "cs": cs, "ce": ce,
            "ss": r.get("startSec"), "se": r.get("endSec"),
            "status": status, "station": r.get("stationName"),
            "session": r.get("night"), "reference": r.get("reference"),
        })
    return dets, skipped, problems


# ---------------------------------------------------------------- audio

class Audio:
    """Decides which detections get a player and where its audio comes from."""

    def __init__(self, args, out_dir):
        self.template = args.audio_url_template
        self.detection_template = None if args.no_detection_links else args.detection_url_template
        self.budget = args.max_clips
        self.out_dir = out_dir
        self.files = {}
        if args.audio_dir:
            for p in Path(args.audio_dir).rglob("*"):
                if p.is_file() and p.suffix.lower() in AUDIO_EXT:
                    self.files.setdefault(p.stem, p)
        self.players = 0
        self.wanted = []      # audioFileIds the page wants
        self.copied = {}      # audioFileId -> relative src

    def src(self, d):
        a = d["audio"]
        if not a:
            return None
        if self.template:
            base = self.template.format(audioFileId=a, id=d["id"], reference=d["reference"] or "",
                                        stationName=d["station"] or "")
        elif a in self.files:
            if a not in self.copied:
                f = self.files[a]
                dest = self.out_dir / "clips" / f.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                self.copied[a] = f"clips/{f.name}"
            base = self.copied[a]
        else:
            return None
        if d["cs"] is not None:
            base += f"#t={d['cs']}" + (f",{d['ce']}" if d["ce"] is not None else "")
        return base

    def link(self, d):
        if not self.detection_template:
            return ""
        url = self.detection_template.format(id=d["id"], reference=d["reference"] or "",
                                             audioFileId=d["audio"] or "", stationName=d["station"] or "")
        return (f'<a class="listen" href="{esc(url)}" target="_blank" rel="noopener" '
                f'title="Open detection {esc(d["id"])}">Listen ↗</a>')

    def __call__(self, d, play=True):
        a = d["audio"]
        window = (f"{d['cs']}–{d['ce']} s" if d["cs"] is not None else "")
        link = self.link(d)
        if a and play and self.players < self.budget:
            if a not in self.wanted:
                self.wanted.append(a)
            url = self.src(d)
            if url:
                self.players += 1
                return (f'<audio controls preload="none" src="{esc(url)}" title="{esc(window)}"></audio>'
                        + (" " + link if link else ""))
        if link:
            return link
        return (f'<span class="clipref" title="audioFileId {esc(a)}">{esc(a or "no recording")}'
                f'{" @ " + esc(window) if window else ""}</span>')


# ---------------------------------------------------------------- coverage

BLOCK_MIN = 15


def infer_recordings(dets, minutes=None):
    """Recordings the export reveals: one per audioFileId that has a detection.
    start = detectedAt - startSec (the same for every detection in a file);
    length = the schedule's cadence (most common gap between starts), unless
    given. A recording with no detections is invisible to this."""
    starts, max_end = {}, 0.0
    for d in dets:
        if not d["audio"] or d["ss"] is None:
            continue
        st = d["when"] - dt.timedelta(seconds=float(d["ss"]))
        st = st.replace(microsecond=0)
        if d["audio"] not in starts or st < starts[d["audio"]]:
            starts[d["audio"]] = st
        if d["se"] is not None:
            max_end = max(max_end, float(d["se"]))
    if not starts:
        return [], None, "none"
    if minutes:
        length, how = float(minutes), "given"
    else:
        ordered = sorted(starts.values())
        gaps = Counter(round((b - a).total_seconds() / 60) for a, b in zip(ordered, ordered[1:])
                       if 1 <= (b - a).total_seconds() / 60 <= 60)
        length, how = (float(gaps.most_common(1)[0][0]), "schedule") if gaps else (15.0, "default")
    length = max(length, math.ceil(max_end / 60))
    recs = sorted((s, s + dt.timedelta(minutes=length)) for s in starts.values())
    return recs, length, how


def _overlap_min(a0, a1, recs):
    tot = 0.0
    for r0, r1 in recs:
        if r1 <= a0 or r0 >= a1:
            continue
        tot += (min(a1, r1) - max(a0, r0)).total_seconds() / 60
    return min(tot, (a1 - a0).total_seconds() / 60)


def coverage(dets, recs, days):
    """Per local date: 15-minute blocks with recorded/dark state and counts."""
    out = []
    for day in days:
        dawn, dusk = civil_for(day)
        base = dt.datetime(day.year, day.month, day.day)
        blocks, rec_min, dark_min, dark_rec = [], 0.0, 0.0, 0.0
        i = 0
        while True:
            b0 = (base + dt.timedelta(minutes=BLOCK_MIN * i)).replace(tzinfo=TZ)
            if b0.date() != day:
                break
            b1 = (base + dt.timedelta(minutes=BLOCK_MIN * (i + 1))).replace(tzinfo=TZ)
            mid = b0 + (b1 - b0) / 2
            dark = mid < dawn or mid >= dusk
            ov = _overlap_min(b0, b1, recs)
            in_b = [d for d in dets if b0 <= d["when"] < b1]
            blocks.append({"start": b0, "end": b1, "dark": dark, "recorded": ov >= BLOCK_MIN / 2,
                           "n": len(in_b), "owl": sum(d["owl"] for d in in_b)})
            rec_min += ov
            if dark:
                dark_min += (b1 - b0).total_seconds() / 60
                dark_rec += ov
            i += 1
        out.append({"date": day, "blocks": blocks, "dawn": dawn, "dusk": dusk,
                    "recorded_min": rec_min, "dark_min": dark_min, "dark_recorded_min": dark_rec})
    return out


def fmt_dur(minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f"{h} h {m:02d} min" if h else f"{m} min"


def render_coverage(cov, recs, length, how, w):
    peak = max((b["n"] for c in cov for b in c["blocks"]), default=0) or 1
    tot_rec = sum(c["recorded_min"] for c in cov)
    tot_dark = sum(c["dark_min"] for c in cov)
    tot_dark_rec = sum(c["dark_recorded_min"] for c in cov)
    pct = (100 * tot_dark_rec / tot_dark) if tot_dark else 0
    w("<div class='section'><h2>Recording coverage</h2><p class='lede'>Each block is 15 minutes; bar height is the number "
      "of detections. Shaded blocks are the hours between civil dusk and civil dawn, the window for owl work. "
      "Coverage is estimated from the detections: a block counts as recorded when a recording in it has at least one "
      "detection, so a recording in which BirdNET heard nothing looks the same as a gap. All times are Pacific Time.</p></div>"
      "<div class='body'>")
    if not recs:
        w("<div class='note'>This export has no recording references, so coverage can't be estimated.</div></div>")
        return
    w(f"<div class='note'><b>{len(recs):,} recordings</b> with detections, about <b>{fmt_dur(tot_rec)}</b> of audio "
      f"({length:g}-minute recordings{', from the recording schedule' if how == 'schedule' else ''}). "
      f"They cover an estimated <b>{fmt_dur(tot_dark_rec)}</b> of the <b>{fmt_dur(tot_dark)}</b> between civil dusk "
      f"and civil dawn ({pct:.0f}%).</div>")
    w("<div class='legend'><span class='lg'><i class='sw sw-day'></i>Recorded, daylight</span>"
      "<span class='lg'><i class='sw sw-night'></i>Recorded, dark</span>"
      "<span class='lg'><i class='sw sw-shade'></i>Civil dusk to civil dawn</span>"
      "<span class='lg'><i class='sw sw-none'></i>No recording with detections</span>"
      "<span class='lg'><i class='sw sw-owl'></i>Owl detection</span></div>")
    for c in cov:
        day = c["date"]
        rise, sets = sun_for(day)
        w(f"<div class='covday'><div class='covhead'><span class='hs-name'>{esc(fmt_date(day))}</span>"
          f"<span class='hs-stats'>civil dawn {esc(fmt_time(c['dawn']))} &bull; sunrise {esc(fmt_time(rise))} &bull; "
          f"sunset {esc(fmt_time(sets))} &bull; civil dusk {esc(fmt_time(c['dusk']))}</span></div><div class='covbar' role='img' "
          f"aria-label='Recording coverage for {esc(fmt_date(day))}'>")
        for b in c["blocks"]:
            cls = ["cb", "dk" if b["dark"] else ""]
            if b["recorded"] or b["n"]:
                cls.append("rn" if b["dark"] else "rd")
                h = f"max(7px,{100 * b['n'] / peak:.0f}%)"
            else:
                cls.append("nr")
                h = "0px"
            if b["owl"]:
                cls.append("ow")
            label = (f"{fmt_time(b['start'])} – {fmt_time(b['end'])}: "
                     + (f"{b['n']} detection{'s' if b['n'] != 1 else ''}" + (f", {b['owl']} owl" if b["owl"] else "")
                        if (b["recorded"] or b["n"]) else "no recording with detections"))
            w(f"<span class='{' '.join(x for x in cls if x)}' style='--h:{h}' title='{esc(label)}'></span>")
        w("</div><div class='covaxis'><span>12 AM PT</span><span>6 AM PT</span><span>12 PM PT</span>"
          "<span>6 PM PT</span><span>12 AM PT</span></div>")
        dpct = (100 * c["dark_recorded_min"] / c["dark_min"]) if c["dark_min"] else 0
        w(f"<div class='sub'>About {fmt_dur(c['recorded_min'])} recorded; {fmt_dur(c['dark_recorded_min'])} of "
          f"{fmt_dur(c['dark_min'])} between civil dusk and civil dawn ({dpct:.0f}%).</div></div>")
    w("</div>")


# ---------------------------------------------------------------- render

def render(dets, doc, args, skipped, problems, out_dir):
    dets.sort(key=lambda d: (-d["conf"], d["when"]))
    clip = Audio(args, out_dir)

    since = parse_ts(doc["since"]).astimezone(TZ) if doc.get("since") else None
    until = parse_ts(doc["until"]).astimezone(TZ) if doc.get("until") else None
    first = since.date() if since else min(d["date"] for d in dets)
    last = (until - dt.timedelta(seconds=1)).date() if until else max(d["date"] for d in dets)

    species = {}
    for d in dets:
        s = species.setdefault(d["sci"], {"com": d["com"], "sci": d["sci"], "n": 0, "night": 0,
                                          "top": d, "days": set(), "owl": d["owl"]})
        s["n"] += 1
        s["night"] += d["dark"]
        s["days"].add(d["date"])
    owls = [d for d in dets if d["owl"]]
    night_n = sum(d["dark"] for d in dets)
    stations = sorted({d["station"] for d in dets if d["station"]})
    refs = sorted({d["reference"] for d in dets if d["reference"]})
    station_names = sorted({station_label(r, args.station_names) for r in refs}) or ["Marymoor Park"]
    codes = sorted({pretty_code(station_code(r)) for r in refs if station_code(r)})
    review = {}
    for d in owls:
        st = owl_status(d["sci"])
        if st != "expected":
            review.setdefault(d["sci"], (d["com"], d["sci"], st))

    out = []
    w = out.append
    range_txt = fmt_date(first) if first == last else \
        f"{first:%B} {first.day} – {last:%B} {last.day}, {last.year}"
    w("<!doctype html><html lang='en'><head><meta charset='utf-8'>")
    w("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    w(f"<title>{esc(args.title)}</title>")
    w("<link rel='preconnect' href='https://fonts.googleapis.com'>")
    w("<link href='https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,300;0,400;0,600;0,700;1,400&display=swap' rel='stylesheet'>")
    if args.logo_uri:
        w(f"<link rel='icon' type='image/png' href='{args.logo_uri}'>")
    w(f"<style>{CSS}{EXTRA_CSS}</style></head><body>")

    mark = f"<img class='logo' src='{args.logo_uri}' alt='Eastside Audubon'>" if args.logo_uri else OWL_SVG
    w("<div class='themebar'><div role='group' aria-label='Colour theme'>"
      "<button type='button' data-t='auto'>Auto</button><button type='button' data-t='light'>Light</button>"
      "<button type='button' data-t='dark'>Dark</button></div></div>")
    w("<header class='mast'><div class='mast-inner'>" + mark + "<div class='mast-text'>")
    w(f"<h1>{esc(args.title)}</h1><div class='kicker'>{esc(args.kicker)}</div>")
    w("<p>Automated acoustic detections from BirdNET listening stations at Marymoor Park, Redmond, WA, "
      "prepared for the Eastside Audubon Society bioacoustics project.</p>")
    w(f"</div><div class='mast-date'>{esc(range_txt)}<br>Marymoor Park, WA"
      + f"<div class='meta'>{esc(', '.join(station_names))}</div>" + "</div></div></header>")

    tiles = [(len(dets), "Detections"), (len(species), "Species"), (night_n, "Night detections"),
             (len(owls), "Owl detections")]
    w("<div class='stats'>" + "".join(f"<div class='stat'><b>{n:,}</b><span>{esc(l)}</span></div>"
                                      for n, l in tiles) + "</div>")

    if args.intro:
        w(f"<div class='section'><h2>This period</h2></div><div class='body intro'>{args.intro}</div>")

    recs, rec_len, rec_how = infer_recordings(dets, args.recording_minutes)
    days = [first + dt.timedelta(days=k) for k in range((last - first).days + 1)]
    cov = coverage(dets, recs, days)
    if not args.no_coverage:
        render_coverage(cov, recs, rec_len, rec_how, w)

    legend = ("<div class='legend'>" + pill("high", "High ≥ 85%") + pill("med", "Medium 70–85%")
              + pill("low", "Low < 70%: not eBird-ready") + pill("night", "Night: sunset → sunrise")
              + pill("owl", "Owl") + "</div>")

    # Owl spotlight
    w("<div class='section'><h2>Owl spotlight</h2><p class='lede'>Every owl detection, ranked by confidence, highest first.</p></div><div class='body'>")
    photos = {}
    if owls:
        if review:
            items = "; ".join(f"{esc(c)} (<i>{esc(s)}</i>) – " +
                              ("rare at Marymoor" if st == "rare" else "not expected at Marymoor, likely misidentification")
                              for c, s, st in review.values())
            w(f"<div class='note'><b>Needs review:</b> {items}. These should be verified from the audio clip.</div>")
        w(legend)
        by_sp = defaultdict(list)
        for d in owls:
            by_sp[d["sci"]].append(d)
        for oi, lst in enumerate(sorted(by_sp.values(), key=lambda l: -l[0]["conf"])):
            top = lst[0]
            st = owl_status(top["sci"])
            badge = "" if st == "expected" else pill("review", "Rare here" if st == "rare" else "Needs review")
            w(f"<details{' open' if oi == 0 else ''}><summary><span class='hs-name'>{esc(top['com'])}</span> "
              f"<span class='sci'>{esc(top['sci'])}</span> {badge}<span class='hs-stats'>{len(lst):,} detections &bull; "
              f"{sum(x['dark'] for x in lst):,} at night &bull; best {top['conf']*100:.1f}%</span></summary>")
            photo = None if args.no_photos else owl_photo(top["sci"], args.photo_cache, args.photo_override.get(top["sci"]))
            photos[top["sci"]] = {k: v for k, v in (photo or {}).items() if k != "data_uri"} or None
            w("<div class='wrap'>" + (photo_figure(photo, top["com"]) if photo else ""))
            w("<table class='sp'><thead><tr><td>#</td><td>Date</td><td>Time</td>"
              "<td>Confidence</td><td></td><td>Clip</td><td class='hide-sm'>Detection ID</td></tr></thead><tbody>")
            for i, d in enumerate(lst[:args.max_owl_rows], 1):
                w(f"<tr><td class='rank'>{i}</td><td>{esc(md(d['date']))}</td><td class='tm'>{esc(fmt_time(d['when']))}</td>"
                  f"<td>{conf_cell(d['conf'])}{review_pill(d['status'])}</td><td>{dn_pill(d)}</td><td>{clip(d)}</td>"
                  f"<td class='hide-sm detid'>{esc(d['id'])}</td></tr>")
            w("</tbody></table>")
            if len(lst) > args.max_owl_rows:
                w(f"<div class='sub'>Showing the top {args.max_owl_rows} of {len(lst):,} detections.</div>")
            w("</div></details>")
    else:
        w("<div class='note'>No owls were detected in this period.</div>")
    w("</div>")

    # Day by day
    w("<div class='section'><h2>Day by day</h2><p class='lede'>Click a day to see its species, ranked by best confidence. "
      "Open a species to see each detection.</p></div><div class='body'>")
    w(legend)
    by_day = defaultdict(list)
    for d in dets:
        by_day[d["date"]].append(d)
    for i, day in enumerate(sorted(by_day, reverse=True)):
        lst = by_day[day]
        rise, sets = sun_for(day)
        sp = defaultdict(list)
        for d in lst:
            sp[d["sci"]].append(d)
        w(f"<details{' open' if i == 0 else ''}><summary><span class='hs-name'>{esc(fmt_date(day))}</span>"
          f"<span class='hs-stats'>{len(sp)} species &bull; {len(lst):,} detections &bull; "
          f"{sum(d['dark'] for d in lst):,} night &bull; {sum(d['owl'] for d in lst):,} owl</span></summary>")
        w(f"<div class='wrap'><div class='sub'>Sunrise {fmt_hm(rise)} &bull; Sunset {fmt_hm(sets)} (computed for Marymoor Park)</div>")
        w("<table class='sp'><thead><tr><td>#</td><td>Species</td><td class='hide-sm'>Scientific name</td>"
          "<td class='num'>Det.</td><td class='num hide-sm'>Night</td><td>Best confidence</td><td>Best clip</td></tr></thead><tbody>")
        ranked = sorted(sp.values(), key=lambda l: -l[0]["conf"])
        for j, sl in enumerate(ranked, 1):
            top = sl[0]
            tag = (" " + pill("owl", "Owl")) if top["owl"] else ""
            w(f"<tr><td class='rank'>{j}</td><td><span class='com'>{esc(top['com'])}</span>{tag}</td>"
              f"<td class='sci hide-sm'>{esc(top['sci'])}</td><td class='num'>{len(sl):,}</td>"
              f"<td class='num hide-sm'>{sum(x['dark'] for x in sl):,}</td><td>{conf_cell(top['conf'])}</td><td>{clip(top)}</td></tr>")
        w("</tbody></table><div class='inner'>")
        for sl in ranked:
            if len(sl) < 2:
                continue
            top = sl[0]
            w(f"<details><summary><span class='com'>{esc(top['com'])}</span> <span class='sci'>{esc(top['sci'])}</span>"
              f"<span class='hs-stats'>{len(sl):,} detections</span></summary><div class='wrap'><table class='sp'><thead><tr>"
              "<td>#</td><td>Time</td><td>Confidence</td><td></td><td>Clip</td><td class='hide-sm'>Detection ID</td></tr></thead><tbody>")
            for k, d in enumerate(sl[:args.max_per_species], 1):
                w(f"<tr><td class='rank'>{k}</td><td class='tm'>{esc(fmt_time(d['when']))}</td><td>{conf_cell(d['conf'])}{review_pill(d['status'])}</td>"
                  f"<td>{dn_pill(d)}</td><td>{clip(d, play=d['owl'] or k <= args.clips_per_species)}</td>"
                  f"<td class='hide-sm detid'>{esc(d['id'])}</td></tr>")
            w("</tbody></table>")
            if len(sl) > args.max_per_species:
                w(f"<div class='sub'>Showing the top {args.max_per_species} of {len(sl):,}.</div>")
            w("</div></details>")
        w("</div></div></details>")
    w("</div>")

    # All species
    w("<div class='section'><h2>All species, ranked by confidence</h2><p class='lede'>Each species' single best detection for the whole period.</p></div><div class='body'>")
    w(f"<details open><summary><span class='hs-name'>Species list</span><span class='hs-stats'>{len(species)} species</span></summary>"
      "<div class='wrap'><table class='sp'><thead><tr><td>#</td><td>Species</td><td class='hide-sm'>Scientific name</td>"
      "<td class='num'>Det.</td><td class='num hide-sm'>Night</td><td class='num hide-sm'>Days</td><td>Best confidence</td>"
      "<td class='hide-sm'>Best at</td><td>Best clip</td></tr></thead><tbody>")
    for j, s in enumerate(sorted(species.values(), key=lambda s: -s["top"]["conf"]), 1):
        tag = (" " + pill("owl", "Owl")) if s["owl"] else ""
        w(f"<tr><td class='rank'>{j}</td><td><span class='com'>{esc(s['com'])}</span>{tag}</td><td class='sci hide-sm'>{esc(s['sci'])}</td>"
          f"<td class='num'>{s['n']:,}</td><td class='num hide-sm'>{s['night']:,}</td><td class='num hide-sm'>{len(s['days'])}</td>"
          f"<td>{conf_cell(s['top']['conf'])}</td><td class='hide-sm'>{esc(md(s['top']['date']))} {esc(fmt_time(s['top']['when']))}</td><td>{clip(s['top'])}</td></tr>")
    w("</tbody></table></div></details></div>")

    gen = dt.datetime.now(TZ)
    exported = parse_ts(doc["exportedAt"]).astimezone(TZ) if doc.get("exportedAt") else None
    minc = doc.get("minConfidence")
    w("<footer>Prepared for the <b>Eastside Audubon Society</b> bioacoustics project. "
      f"Detections from {esc(', '.join(station_names))}"
      + (f" ({esc(', '.join(codes))})" if codes else "") + ". "
      + (f"Export of {exported:%B} {exported.day}, {exported.year}" if exported else "Export")
      + (f", detections at or above {float(minc)*100:.0f}% confidence. " if minc is not None else ". ")
      + "Identifications by <a href='https://birdnet.cornell.edu/'>BirdNET</a> (K. Lisa Yang Center for Conservation Bioacoustics, "
      "Cornell Lab of Ornithology, and Chemnitz University of Technology), model licensed CC BY-NC-SA 4.0. "
      "Night is computed sunset to sunrise for Marymoor Park; the coverage chart's dark window is civil dusk to civil dawn "
      "(sun 6° below the horizon), and its coverage is estimated from recordings with detections. All times are Pacific Time (PT). "
      "Owl photos are CC-licensed iNaturalist observations from the Seattle area, credited beside each photo. Confidence bands: High ≥ 85%, Medium 70–85%, Low &lt; 70%. "
      f"Generated {gen:%B} {gen.day}, {gen.year}.</footer>" + THEME_JS + "</body></html>")

    summary = {
        "period": {"first": first.isoformat(), "last": last.isoformat(),
                   "since": doc.get("since"), "until": doc.get("until")},
        "export": {k: doc.get(k) for k in ("exportedAt", "model", "minConfidence", "total", "sort", "order")},
        "records_in_file": len(doc["detections"]),
        "detections_used": len(dets),
        "skipped": dict(skipped),
        "problems": dict(problems),
        "species": len(species),
        "night_detections": night_n,
        "owl_detections": len(owls),
        "high_conf": sum(d["conf"] >= HIGH for d in dets),  # not shown on the page
        "stations": station_names, "references": refs,
        "owl_photos": photos,
        "review_status": dict(Counter(d["status"] for d in dets)),
        "owls_by_species": {s["sci"]: {"common": s["com"], "count": s["n"], "night": s["night"],
                                       "best_conf": round(s["top"]["conf"], 4),
                                       "best_at": s["top"]["when"].isoformat(),
                                       "best_id": s["top"]["id"], "status": owl_status(s["sci"])}
                            for s in species.values() if s["owl"]},
        "owl_review": [{"common": c, "sci": s, "status": st} for c, s, st in review.values()],
        "species_list": [{"common": s["com"], "sci": s["sci"], "count": s["n"], "night": s["night"],
                          "best_conf": round(s["top"]["conf"], 4)}
                         for s in sorted(species.values(), key=lambda s: -s["top"]["conf"])],
        "coverage": {
            "estimated": True,
            "basis": "recordings with at least one detection; silent recordings are not visible",
            "recordings_with_detections": len(recs), "recording_minutes": rec_len, "length_from": rec_how,
            "recorded_min": round(sum(c["recorded_min"] for c in cov)),
            "dark_window_min": round(sum(c["dark_min"] for c in cov)),
            "dark_window_recorded_min": round(sum(c["dark_recorded_min"] for c in cov)),
            "days": [{"date": c["date"].isoformat(), "civil_dawn": fmt_time(c["dawn"]), "civil_dusk": fmt_time(c["dusk"]),
                      "recorded_min": round(c["recorded_min"]), "dark_window_min": round(c["dark_min"]),
                      "dark_window_recorded_min": round(c["dark_recorded_min"]),
                      "unrecorded_dark_blocks": [fmt_time(b["start"]) for b in c["blocks"]
                                                 if b["dark"] and not b["recorded"] and not b["n"]]}
                     for c in cov],
        },
        "audio": {"recordings_wanted": len(clip.wanted), "players": clip.players,
                  "copied_to_clips_folder": len(clip.copied),
                  "detection_links": bool(clip.detection_template),
                  "source": "template" if args.audio_url_template else "audio-dir" if args.audio_dir else "none"},
    }
    return "".join(out), summary, clip.wanted


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Marymoor Park BirdNET Sightings")
    ap.add_argument("--kicker", default="Eastside Audubon bioacoustics project")
    ap.add_argument("--intro-file", help="HTML fragment for the 'This period' summary")
    ap.add_argument("--audio-dir", help="folder of recordings named <audioFileId>.<ext>; copied to clips/ next to the page")
    ap.add_argument("--audio-url-template", help="URL for a recording, e.g. https://host/audio/{audioFileId}.wav")
    ap.add_argument("--detection-url-template", default=DETECTION_URL,
                    help="per-detection page with audio; fields {reference} {id} {audioFileId} {stationName}")
    ap.add_argument("--no-detection-links", action="store_true")
    ap.add_argument("--logo", default=str(Path(__file__).resolve().parent.parent / "assets" / "eas-logo.png"))
    ap.add_argument("--no-logo", action="store_true", help="plain owl mark instead of the EAS logo")
    ap.add_argument("--station-name", action="append", default=[], metavar="CODE=NAME",
                    help="friendly station name, e.g. SR01='Marymoor Park Station' (adds to the built-in list)")
    ap.add_argument("--no-photos", action="store_true", help="skip the owl photos")
    ap.add_argument("--photo", action="append", default=[], metavar="SCI=OBSERVATION_ID",
                    help="use a specific iNaturalist observation for an owl species")
    ap.add_argument("--no-coverage", action="store_true", help="leave out the recording coverage section")
    ap.add_argument("--recording-minutes", type=float,
                    help="length of each recording (default: worked out from the recording schedule)")
    ap.add_argument("--start", help="first local date to include (YYYY-MM-DD)")
    ap.add_argument("--end", help="last local date to include (YYYY-MM-DD)")
    ap.add_argument("--min-conf", type=float, default=0.0)
    ap.add_argument("--max-clips", type=int, default=150, help="cap on audio players")
    ap.add_argument("--clips-per-species", type=int, default=1)
    ap.add_argument("--max-per-species", type=int, default=0, help="rows per species per day (0 = all)")
    ap.add_argument("--max-owl-rows", type=int, default=0, help="rows per owl species (0 = all)")
    args = ap.parse_args()
    args.max_per_species = args.max_per_species or 10**9
    args.max_owl_rows = args.max_owl_rows or 10**9

    args.intro = Path(args.intro_file).read_text() if args.intro_file else ""
    args.station_names = dict(STATION_NAMES)
    for kv in args.station_name:
        k, v = kv.split("=", 1)
        args.station_names[k.replace("-", "").upper()] = v
    args.photo_override = dict(kv.split("=", 1) for kv in args.photo)
    args.photo_cache = Path(args.out).resolve().parent / ".owl-photos"
    args.logo_uri = None
    if not args.no_logo and Path(args.logo).exists():
        args.logo_uri = "data:image/png;base64," + base64.b64encode(Path(args.logo).read_bytes()).decode()

    doc = load(args.input)
    dets, skipped, problems = normalise(doc)
    if args.start:
        dets = [d for d in dets if d["date"] >= dt.date.fromisoformat(args.start)]
    if args.end:
        dets = [d for d in dets if d["date"] <= dt.date.fromisoformat(args.end)]
    if args.min_conf:
        dets = [d for d in dets if d["conf"] >= args.min_conf]
    if not dets:
        raise SystemExit(f"No usable bird detections. Skipped: {dict(skipped)} Problems: {dict(problems)}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    page, summary, wanted = render(dets, doc, args, skipped, problems, out.parent)
    out.write_text(page, encoding="utf-8")
    out.with_suffix(".summary.json").write_text(json.dumps(summary, indent=2, default=str))
    out.with_suffix(".clips.json").write_text(json.dumps(wanted, indent=2))

    warn = []
    if doc.get("total") is not None and doc["total"] != len(doc["detections"]):
        warn.append(f"header total {doc['total']} != {len(doc['detections'])} detections in file (export may be truncated)")
    if problems:
        warn.append(f"rows with problems: {dict(problems)}")
    if summary["audio"]["source"] == "none" and not summary["audio"]["detection_links"]:
        warn.append("no audio source or detection links: clips show as audioFileId @ window")
    if summary["audio"]["detection_links"] and not all(d["reference"] for d in dets):
        warn.append("some detections have no 'reference'; their detection links will be broken")
    elif summary["audio"]["source"] != "none" and summary["audio"]["players"] < summary["audio"]["recordings_wanted"]:
        warn.append("some recordings were not found; those clips show as audioFileId @ window")
    print(json.dumps({k: summary[k] for k in ("period", "records_in_file", "detections_used", "skipped", "species",
                                               "night_detections", "owl_detections", "owl_review", "owl_photos",
                                               "review_status", "audio")}, indent=2, default=str))
    for x in warn:
        print("WARNING:", x)
    print(f"wrote {out} ({out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    main()
