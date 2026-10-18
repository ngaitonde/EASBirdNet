---
name: marymoor-birdnet-json-report
description: Turn a Marymoor BirdNET detections export (a detections-FROM-to-TO.json file with exportedAt/since/until/total and a detections list of id, audioFileId, detectedAt, commonName, scientificName, confidence, clip, reviewStatus, reference, stationName, night) into an HTML bird-sightings report for the Eastside Audubon Society bioacoustics project, styled like the EAS eBird Weekly newsletter with the EAS logo, with light and dark themes. The report has a recording-coverage chart, a day-by-day breakdown, audio clips, common and scientific names, confidence ranked highest to lowest, and a night-time owl focus for improving Marymoor eBird data. Use this whenever the user attaches or points to a detections JSON from the Marymoor station, or any BirdNET detections file, and asks for a report, sightings summary, owl report, nightly or weekly write-up, or owl spotlight, even if they don't name the skill.
---

# Marymoor Park BirdNET report from a detections export

**Audience:** the Eastside Audubon Society (EAS) bioacoustics project.
**Purpose:** improve eBird data for Marymoor Park at night, with a focus on owls.

Reviewers use this page to decide what goes into eBird. Correct numbers, honest confidence labels and clips they can play matter more than polished prose.

**Input:** one export file, `detections-<from>-to-<to>.json`, covering a day or a week. Birdsense's Detections screen saves it with **Export as JSON**. Its fields, and how each one is used, are in `references/export-format.md`. Read that reference if a file looks different from what's described here.

## Ground rules

- **Use only the species and detections in the export.** Don't add species from general knowledge or eBird. Every number you write must come from the script's `summary.json`.
- **Do all counting and ranking in `scripts/build_report.py`.** A week can hold thousands of detections, and hand-counting is how wrong numbers get published.
- **Keep doubtful detections, but label them.** Low-confidence rows and unexpected species stay in the report, never presented as eBird-ready. The EAS reviewers make the call.

## Workflow

### 1. Build

```bash
python3 -I <skill-dir>/scripts/build_report.py <export.json> --out <user-folder>/reports/marymoor-birdnet-<from>[_<to>].html
```

The script prints the period, the counts and any warnings. Act on the warnings:

- **`header total … != … detections`:** the export may be truncated. Tell the user, and don't present the report as complete.
- **`rows with problems`:** some detections lack required fields. Report how many.
- **Audio warnings:** see step 3.

Options that change what the report covers:

- **`--start` / `--end` (YYYY-MM-DD, local dates):** narrow the report to part of the file.
- **`--min-conf`:** raise the confidence floor above the export's `minConfidence`. Use it only when the user asks; the confidence bands already separate weak detections.

The script writes three files next to the page:

- **`.summary.json`:** every number the page shows, the owls by species with their best detection ID, the owl review list, the species list and the review statuses.
- **`.clips.json`:** the `audioFileId`s whose recordings the page wants to play.
- **The HTML page itself.**

### 2. Read the results and write "This period"

Read `summary.json`, then look past the counts.

**Owls.** The script sorts each owl species by how likely it is at Marymoor:
- **Expected:** Barred, Great Horned, Barn, Western Screech-, Northern Saw-whet and Short-eared Owl.
- **"Rare here":** Long-eared, Northern Pygmy- and Snowy Owl.
- **"Needs review":** every other owl. Eastern Screech-Owl, for example, is a common BirdNET confusion with Western Screech-Owl here.

**Other unlikely species.** Scan the species list for birds unusual in a King County lowland park, such as eastern-Washington or mountain species. Black-billed Magpie, Mountain Chickadee, Cassin's Finch and American Tree Sparrow are examples. Base this only on species that are in the file.

Then write two short paragraphs as an HTML fragment (`<p>` tags) and rebuild with `--intro-file`:
1. **Owls:** each owl species, how many detections, when, and the best confidence. If it's rare at Marymoor, say so.
2. **Overall:** detections, species and night detections from `summary.json`. Then name the unusual species, each with its best confidence, as possible misidentifications.
3. **Coverage (one or two sentences):** from `summary.json` → `coverage`, how much of the civil-dusk-to-civil-dawn window the recordings cover. Always call it an estimate. If the empty night blocks cluster, say where, for example "no recordings with detections between 7:00 PM PT and 9:30 PM PT".

How to write them:
- **State facts; don't advise on listening.** Don't say which clip to listen to first or how to listen. End each paragraph by saying the detections should be verified from the audio clip.
- **Write times as the page does:** hour and minute, AM or PM, then "PT", with no seconds, e.g. "2:41 AM PT". This applies to every time, including both ends of a range: "between 2:41 AM PT and 4:43 AM PT", never "between 2:41 and 4:43 AM PT".
- **Call the station by its friendly name** ("Marymoor Park Station"), not the reference code.

### 2b. Recording coverage

The coverage section shows when the recorder was running and how much of the owl window it sampled. It follows the "Recording coverage" chart in the EAS Marymoor Owl Listening Pilot report:
- one strip per local date, made of 96 blocks of 15 minutes
- bar height is the block's detection count
- shaded blocks run from civil dusk to civil dawn (sun 6° below the horizon)
- an owl dot marks blocks with an owl detection

**It is an estimate, and the page says so.** The export lists detections, not recordings:
- Each recording is identified by its `audioFileId`.
- Its start time is `detectedAt − startSec`, the same for every detection in that file.
- Its length is the recording schedule's cadence: the most common gap between start times, 15 minutes at Marymoor.
- A recording in which BirdNET detected nothing doesn't appear in the export, so it looks the same as a time the recorder was off.

Gaps are most likely at night, when little calls, so the estimate can understate night coverage. Never present a gap as proof the recorder was off. Describe it as "no recording with detections".

The app's database does store every recording (`AudioFile.recordedAt`, `durationSec`, `detectionCount` in `backend/internal/db/models.go`), but the export doesn't include them. If a future export adds a recordings list, switch the coverage section to use it.

- `summary.json` → `coverage` has the totals, each day's civil dawn and dusk, and the list of dark blocks with no recording.
- If the recording schedule isn't regular, pass `--recording-minutes N`.
- `--no-coverage` leaves the section out.

### 3. Audio

**Detection links (always on).** Every detection row gets a "Listen ↗" link to its page in the EAS owl app. That covers the owl spotlight, the day-by-day tables and their nested lists, and each species' best detection in the all-species table:
`https://owls.eastsideaudubon.org/app/detections/{reference}/{id}`, for example `…/detections/OWL-20261016-SR01/det_389ed020c669a66bae4c041faa0e6c9f`.
- That page plays the detection's audio, so reviewers can listen even without the options below.
- Before delivering, check one link from the report, for example with `curl -sL -o /dev/null -w "%{http_code}"`, and confirm it returns 200.
- If the app's address changes, pass `--detection-url-template`. It can use `{reference}`, `{id}`, `{audioFileId}` and `{stationName}`.
- `--no-detection-links` turns the links off.

**Inline players (optional).** Each detection points to a spot inside a longer recording: its `audioFileId` plus `clip.startSec` and `clip.endSec`. The script adds `#t=start,end` to each player, so playback starts at the call.

The export doesn't contain the audio itself, so it needs a source:

- **The user has the recordings as files**, named `<audioFileId>.wav`, `.mp3`, `.flac` or similar: pass `--audio-dir <folder>`. The script copies only the recordings the page uses into a `clips/` folder next to the HTML. The page and that folder are delivered together.
- **The recordings are on a web server:** pass `--audio-url-template 'https://host/path/{audioFileId}.wav'`. The template can also use `{id}`, `{reference}` and `{stationName}`. A link to a home or private network won't play for EAS readers, so say so if the host looks private (192.168.x, .local, localhost).
- **Neither:** the "Listen ↗" links are enough; no players appear. Mention that inline players can be added if the user supplies the recordings or a URL pattern for them.

If the script reports `some recordings were not found`, list how many of the IDs in `.clips.json` are missing.

### 3b. Owl photos

Each owl card in the spotlight shows a photo of that exact species, so readers can picture the bird. The script picks it automatically:
- **Source:** iNaturalist research-grade observations within 40 km of Marymoor (Seattle and the Eastside).
- **Exact species:** the observation's taxon must equal the scientific name, at species rank.
- **Licence:** Creative Commons only: CC0, BY, BY-SA, BY-NC or BY-NC-SA. The non-commercial licences fit EAS's non-commercial use.
- **Choice:** a named local place (a park or city) is preferred, then the most-faved observation.
- **Embedding:** the image is built into the page.
- **Credit:** every photo gets a full Creative Commons credit in the usual Title, Author, Source, Licence form, each part linked:
  “Great Horned Owl” by Evan, via iNaturalist observation 267181957, licensed under CC BY-NC.
  The title links to the photo page, the author to their iNaturalist profile, the source to the observation, and the licence to the CC deed. The caption also gives the place and month, and says the photo is illustrative, not from this recording.
- **Licence wording:** the licence is named exactly as iNaturalist gives it ("CC BY-NC"), because its API doesn't state a version. Don't add a version number that isn't in the data.
- **Never remove or shorten a credit**, even to save space. Displaying a CC photo depends on giving the credit.
- **Cache:** downloads are kept in `.owl-photos/` next to the report, so rebuilds don't refetch.

**Look at every chosen photo before delivering.** Open each `.owl-photos/*.jpg` with Read and check that it clearly shows that owl:
- the right species
- the bird visible, not a speck
- not a feather, a pellet or a sound recording

If a photo fails, pick a better observation by looking at the next results from the iNaturalist API, then rebuild with `--photo "Bubo virginianus=<observation id>"`.

If the lookup fails, for example because there's no network, the card renders without a photo and the script prints a warning. Tell the user.

### 4. Deliver

The page carries the EAS Steller's Jay logo (`assets/eas-logo.png`, the bird-only mark from the EAS newsletter, not the wide wordmark in `frontend/images/eas-logo.png`), embedded in the page and used as the browser-tab icon. This matches the newsletter at https://jjs52.github.io/eas-newsletter/index.html.

**With the logo (the default): deliver files, not an Artifact.**
1. Save the HTML, plus `clips/` if there is one, in the user's folder.
2. Give the user the HTML, using a file-sharing tool if the session has one. If there's a `clips/` folder, zip it with the page and share the zip.
3. Don't publish it as an Artifact. The logo is EAS's branding, so EAS decides where the page is hosted.
4. Tell the user they can post it wherever EAS hosts pages, such as the GitHub Pages site the newsletter lives on, or attach it to an email.

**If the user asks for a Claude-hosted link: rebuild with `--no-logo` and publish that as an Artifact.** The `--no-logo` version shows a plain owl mark instead.
1. Load `artifact-design` first.
2. Title it "Marymoor BirdNET Sightings", put the date range in the description, and use icon `bird`.
3. To give it audio, load `artifact-capabilities` and upload the recordings as assets. Then rebuild with `--audio-url-template`, pointing at the asset URLs, and republish.

**In both cases, don't hand-edit the page.** Change it through the script's options, or edit the script itself so the fix carries over to future reports.

### 5. Check before finishing

1. **Totals:** compare the page's stat tiles with `summary.json`. Also recount detections and species straight from the export with a few lines of Python; the two must agree.
2. **Rendering:** open the page through a local static server, since the browser pane can't open local files directly. Confirm the masthead logo, the owl spotlight and the day cards. If there's audio, confirm a player loads.
3. **Final message:** keep it short:
   - the file
   - the date range
   - detections, species and night detections
   - the estimated coverage of the civil-dusk-to-civil-dawn window
   - each owl species with its best detection (time, confidence)
   - the review items
   - the state of the audio: whether the detection links were checked, and whether inline players are present
   - the owl photos used, with photographer and place

## What the page contains

The styling follows the EAS eBird Weekly: Source Sans 3, the navy masthead (#1a375f) with the logo, the blue stat row (#0068a6), fold-open bordered cards holding species tables, and a navy footer. It works on phones and in dark mode.

The sections, in order:

0. **Theme switch:** a top bar with Auto, Light and Dark buttons. Auto follows the reader's device setting. The reader's choice is remembered in their browser where storage is allowed.
1. **Masthead:** the logo, the title, "Eastside Audubon bioacoustics project", one sentence on where the detections come from, the date range and the station's friendly name. Keep the masthead to that; it carries no statement of aims and no verification note.
2. **Stat tiles, in this order:** Detections, Species, Night detections, Owl detections.
3. **This period:** your paragraphs: owls, overall, coverage.
4. **Recording coverage:** the estimated-coverage note with totals, a legend, and one 96-block strip per day. Each strip has a header giving civil dawn, sunrise, sunset and civil dusk, an axis labelled 12 AM PT to 12 AM PT, and a line for that day's recorded and dark-window minutes.
5. **Owl spotlight:** one card per owl species, with a small (120px) CC-licensed photo and its full credit (title, author, source, licence). Every detection is listed, ranked by confidence highest first, with date, time, confidence band, day or night, Listen link and detection ID.
6. **Day by day:** one card per local date, newest first:
   - computed sunrise and sunset for the date
   - species ranked by best confidence: common name, scientific name, detections, night count, best confidence and best clip
   - a nested card per species with its detections ranked by confidence, each with clip and ID
7. **All species ranked:** each species' best detection over the whole period, with a Listen ↗ link to that detection, as in the owl spotlight. When two detections tie, the earlier one is linked.
8. **Footer:** the EAS project credit, the station's friendly name and code (e.g. "Marymoor Park Station (SR-01)"), export date and `minConfidence`, the BirdNET credit (Cornell Lab and TU Chemnitz, CC BY-NC-SA 4.0), the photo-source note, definitions, and the generated date.

There is deliberately no eBird-candidates section. Leave it out unless the user asks for it again.

**Conventions:**
- **Times:** always hour and minute with AM or PM, labelled PT (Pacific Time), never with seconds.
- **Themes:** light and dark are both fully styled. Check both before delivering, using the theme switch.
- **Station names:** friendly names come from `STATION_NAMES` in the script, keyed by the code at the end of `reference` (`OWL-20261016-SR01` → `SR01` → "Marymoor Park Station"). For a new station, ask the user for its friendly name. Pass it with `--station-name SR02="…"`, and add it to `STATION_NAMES` so later reports use it automatically.

**Definitions used:**
- **Night:** sunset to sunrise at Marymoor (47.661, −122.118), America/Los_Angeles, computed for each date. Used for the Night pills and counts.
- **Dark window (coverage chart only):** civil dusk to civil dawn, the same window the EAS pilot report used.
- **Confidence bands:** High ≥ 0.85, Medium 0.70–0.85, Low < 0.70.
- **Owls:** families Strigidae and Tytonidae.

## Script options

| Option | Use |
|---|---|
| `--detection-url-template URL` / `--no-detection-links` | Per-detection Listen link (on by default, see step 3) |
| `--audio-dir DIR` / `--audio-url-template URL` | Inline audio players (see step 3) |
| `--intro-file F` | "This period" HTML fragment |
| `--station-name CODE=NAME` | Friendly station name (SR01 → Marymoor Park Station is built in) |
| `--photo SCI=OBS_ID` / `--no-photos` | Choose a specific iNaturalist observation for an owl / leave photos out |
| `--recording-minutes N` / `--no-coverage` | Length of each recording for the coverage estimate (default: from the schedule) / leave the coverage section out |
| `--start`, `--end`, `--min-conf` | Narrow the period or raise the confidence floor |
| `--no-logo`, `--logo PNG` | Plain owl mark / a different logo |
| `--title`, `--kicker` | Masthead text |
| `--max-clips N` | Cap on audio players (default 150) |
| `--clips-per-species N` | Players per species per day in the nested lists (default 1; owls always get players) |
| `--max-per-species N`, `--max-owl-rows N` | Row caps. The default is every detection, so each one has its Listen link; cap only if a very large week makes the page unwieldy. |
