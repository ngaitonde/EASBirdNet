# Detections export format

This is the file Birdsense's Detections screen saves with **Export as JSON** (`ExportResponse` in `backend/internal/api/shapes.go`; detection fields from `Detection` there). Files are named `detections-<from>-to-<to>.json`, for example `detections-2026-10-14-to-2026-10-14.json`. Each file is one JSON object.

```json
{
  "exportedAt": "2026-10-18T04:28:38.487591725Z",
  "model": "birdnet",
  "since": "2026-10-14T07:00:00Z",
  "until": "2026-10-15T07:00:00Z",
  "minConfidence": 0.5,
  "sort": "heard",
  "order": "desc",
  "total": 725,
  "detections": [
    {
      "id": "det_db23f785a4e82c5725834b1a5e6770a4",
      "audioFileId": "af_5d6920ef59fec5887a3be6267ed56ec9",
      "startSec": 282,
      "endSec": 285,
      "detectedAt": "2026-10-15T05:36:50Z",
      "scientificName": "Glaucidium gnoma",
      "commonName": "Northern Pygmy-Owl",
      "confidence": 0.7294,
      "clip": {"startSec": 281, "endSec": 286},
      "reviewStatus": "unreviewed",
      "model": "birdnet",
      "reference": "OWL-20261016-SR01",
      "stationName": "Marymoor",
      "night": "2026-10-14"
    }
  ]
}
```

## Header

| Field | Meaning | How the report uses it |
|---|---|---|
| `since` / `until` | UTC window of the export. `until` is exclusive. `07:00Z` is local midnight during PDT, `08:00Z` during PST. | The report's date range: `since` converted to local time, through `until` minus 1 second. |
| `total` | Number of detections the exporter says it wrote. | Compared with the length of `detections`. A mismatch means the export may be truncated. The script warns, and you must tell the user. |
| `minConfidence` | Detections below this score were never exported. | Stated in the footer, so readers know absent species may simply have scored low. |
| `exportedAt` | When the file was made, with nanosecond precision. | Shown in the footer. |
| `model`, `sort`, `order` | Exporter settings. | Recorded in `summary.json` only. |

## Detection

| Field | Meaning | How the report uses it |
|---|---|---|
| `id` | Stable detection ID. | Shown in the Detection ID column. Combined with `reference` to build the Listen link: `https://owls.eastsideaudubon.org/app/detections/{reference}/{id}`. |
| `detectedAt` | UTC time of the call. | Converted to America/Los_Angeles. This drives the day grouping and the day/night tag. |
| `commonName`, `scientificName` | BirdNET label. | Shown as given. Species are grouped by scientific name. |
| `confidence` | Score from 0 to 1. | Ranking and confidence bands. |
| `audioFileId` | The recording the call is in, usually several minutes long. | The source of the audio player (see the audio section in SKILL.md). |
| `startSec`, `endSec` | The 3-second BirdNET analysis window inside that recording. | Fallback for the clip window. |
| `clip.startSec`, `clip.endSec` | Optional: absent until a clip is cut. The window padded by 1 second on each side, for listening. | Becomes a media fragment `#t=start,end`, so the player jumps to the call. |
| `reviewStatus` | One of `unreviewed`, `confirmed` or `rejected` (`db.Review*` in `backend/internal/db/models.go`). | `confirmed` gets a green "Verified" pill. `rejected` detections are dropped and counted under `skipped`. |
| `reference` | Recording deployment or session code, e.g. `OWL-20261016-SR01`. | Part of the Listen link. Its station code (`SR01`) maps to the friendly name "Marymoor Park Station", which the page shows instead of the raw code. |
| `stationName` | Station name, e.g. `Marymoor`. | Not shown; the friendly name from `reference` is used. |
| `night` | The recording session's start date. It labels the whole session, including daytime detections; a 5:13 PM call can carry `night: 2026-10-14`. | Not used in the report. Darkness is computed from sunset and sunrise instead. |
