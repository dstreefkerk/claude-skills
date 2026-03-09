---
name: stream-transcript
description: >
  Extract plaintext WebVTT transcripts and detect slide transitions from Microsoft Stream
  (on SharePoint) video recordings. Use when the user wants to download, extract, or retrieve
  a transcript/captions from a Microsoft Stream video, Teams meeting recording, or
  SharePoint-hosted video. Also supports detecting slide changes and capturing screenshots.
  Triggers: "get the transcript", "download transcript", "extract captions",
  "stream transcript", "meeting recording transcript", "detect slides",
  "capture slides", "slide transitions". Requires the Playwright MCP server for browser
  authentication.
---

# Stream Transcript & Slide Extractor

Extract plaintext WebVTT transcripts and detect visual slide transitions from Microsoft
Stream videos hosted on SharePoint.

## Capabilities

- **Transcript extraction**: Download plaintext WebVTT transcripts via the SharePoint REST API
- **Slide detection**: Detect visual changes (slide transitions) in the video and capture PNG screenshots of each distinct slide

The CDN endpoint encrypts transcripts, but the REST API returns them in plaintext.
Slide detection uses canvas-based frame comparison within the Playwright browser context.

## Success Criteria

1. A `.vtt` file exists on disk at the expected output path
2. File size is >0 bytes
3. File begins with the `WEBVTT` header
4. Before declaring success, verify all three criteria using `head` and `wc -c` on the saved file

## Prerequisites

- Playwright MCP server must be configured (for browser-based SharePoint authentication)
- **Always use Playwright** (`headless: false`), not chrome extension tools — the user needs to see the browser window to complete SharePoint SSO authentication
- User must be able to authenticate to their SharePoint tenant in the browser

## Workflow

### Step 1: Identify the video

Get the Stream video URL from the user. It will look like:

```text
https://{tenant}-my.sharepoint.com/personal/{user}/_layouts/15/stream.aspx?id={filePath}
```

If the user provides a driveId and itemId directly, skip to Step 3.

### Step 2: Authenticate and resolve IDs

Use Playwright to navigate to the Stream URL with `headless: false` so the user can authenticate.

```text
playwright_navigate({ url: streamUrl, headless: false, timeout: 90000 })
```

Wait for the page to load, then inject `scripts/resolve-drive-item.js` and resolve the IDs:

```javascript
// After injecting the script via playwright_evaluate:
await window.ResolveDriveItem.run()
// Returns JSON: { driveId, itemId, filePath, method }
```

The script tries four resolution methods in order of reliability:
1. **Sharing/encoding API** (most reliable) -- encodes the file URL as a share token
2. **Script tag search** -- finds `drives/xxx/items/xxx` patterns in page JS
3. **SharePoint REST API** -- `GetFileByServerRelativeUrl` for partial metadata
4. **Page context** -- `_spPageContextInfo` hydration data

### Step 3: List available transcripts

Call the transcript listing endpoint from the authenticated browser:

```javascript
(async () => {
    const r = await fetch(
        `/_api/v2.1/drives/${driveId}/items/${itemId}/media/transcripts`,
        { credentials: 'include', headers: { 'Accept': 'application/json' } }
    );
    const data = await r.json();
    return JSON.stringify(data.value.map(t => ({
        id: t.id,
        displayName: t.displayName,
        languageTag: t.languageTag,
        size: t.size,
        temporaryDownloadUrl: t.temporaryDownloadUrl
    })));
})();
```

### Step 4: Download and save the transcript

**Primary approach: Fetch via REST API** (most reliable — returns plaintext VTT):

```javascript
(async () => {
    const r = await fetch(
        `/_api/v2.1/drives/${driveId}/items/${itemId}/media/transcripts/${transcriptId}/content`,
        { credentials: 'include', headers: { 'Accept': '*/*' } }
    );
    // Returns plaintext WebVTT (text/vtt content type)
    const vtt = await r.text();
    window.__transcript = vtt;
    return 'Transcript fetched: ' + vtt.length + ' bytes';
})();
```

> **Why not temporaryDownloadUrl?** The `temporaryDownloadUrl` from Step 3 usually points to a `/streamContent` endpoint that returns AES-encrypted content, not plaintext VTT. The REST API `/content` endpoint above is the reliable plaintext path.

**Fallback: temporaryDownloadUrl with curl** (only if REST API fails):

If the REST API returns errors, try the `temporaryDownloadUrl` with curl. It expires quickly, so use it immediately after Step 3. Test with `head -1` to confirm the file starts with `WEBVTT`:

```bash
curl -s -o "<output_path>/transcript.vtt" "<temporaryDownloadUrl>"
```

### Saving from browser memory to disk

When saving from browser memory, **do not** extract raw text through the conversation (wastes context tokens). Instead:

1. Test the save pipeline first with a small sample (e.g., `window.__transcript.substring(0, 100)`)
2. Encode as base64 in the browser: `btoa(unescape(encodeURIComponent(window.__transcript)))`
3. Split into chunks (~50KB each) and request each via `playwright_evaluate`
4. Chunks that exceed tool output limits are saved automatically to tool-result files
5. For any chunks returned inline or needing manual saving, **use the Write tool** (not bash heredocs — base64 content breaks shell escaping)
6. Decode all chunks with a Python script:

```python
import json, base64, os
# Read base64 from tool-result JSON files + any Write-tool-created chunk files
# Concatenate all base64 strings, then:
decoded = base64.b64decode(b64_all).decode('utf-8')
open('transcript.vtt', 'w', encoding='utf-8').write(decoded)
```

## API Reference

See [references/api_endpoints.md](references/api_endpoints.md) for the full API endpoint reference.

## Troubleshooting

- **401/403 errors**: Session may have expired. Re-navigate to the Stream page to refresh auth.
- **404 on media/transcripts**: The video may not have a transcript. Check if captions are visible in the player.
- **Empty transcript list**: The recording may not have had transcription enabled during the meeting.
- **Encrypted content from CDN**: You're hitting the wrong endpoint. Use `_api/v2.1` (not `_api_cached`). The `_api_cached/.../cdnmedia/transcripts` endpoint returns AES-encrypted content that requires a client-side key. Always use the REST API path instead.

---

## Slide Transition Detection

Detect visual changes in Teams recordings and capture screenshots of each slide/screen state.

### Quick Start

1. Navigate Playwright to the Stream video URL (same auth as transcript extraction)
2. Read and inject `scripts/slide-detector.js` via `playwright_evaluate`
3. Start the scan async and poll for progress:

```javascript
// Start scan
window.SlideDetector.run({ coarseInterval: 60, threshold: 10 })
  .then(r => { window._result = r; window._done = true; });

// Poll progress (0-100)
window.SlideDetector.progress

// Abort if needed
window.SlideDetector.abort()
```

1. Retrieve the manifest from `window._sdResult` (data URLs stored separately in `window._sdScreenshots`)
2. Save PNGs to disk using `scripts/screenshot-saver.js` (see below)

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `coarseInterval` | `60` | Seconds between samples. Use 60 to avoid Stream session timeout. |
| `threshold` | `10` | Min diff score for a change. 10 works well for slides. |
| `captureRegion` | `{x:0, y:0, w:0.75, h:1.0}` | Left 75% of frame (slide area in Teams presenter mode). |

### Step 7: LLM Post-Processing

After saving screenshots to disk, use **sub-agents** (Task tool with `subagent_type: "general-purpose"`) to classify and describe each slide. This avoids loading all images into the main context.

Launch one sub-agent per batch of ~5 screenshots. Each sub-agent should:

1. Read the PNG files assigned to it
2. For each screenshot, determine: content type (`slide`, `screen-share`, `gallery-view`, `transition-artifact`, `duplicate`), slide title, brief description, and whether it duplicates an earlier slide
3. Return a JSON array of enriched transition objects

After all sub-agents complete, merge their results into the final manifest. Filter out entries where `isContent` is `false` (webcam-only frames) or `contentType` is `transition-artifact`.

See [references/slide_detection.md](references/slide_detection.md) for the full LLM post-processing prompt template, field definitions, and enhanced output format.

### Saving Screenshots to Disk

After slide detection completes, inject `scripts/screenshot-saver.js` and loop:

```javascript
// 1. Inject screenshot-saver.js via playwright_evaluate
// 2. Initialize:
window.ScreenshotSaver.init()   // -> { status: "ready", total: N }
// 3. Loop: call next(), then screenshot:
window.ScreenshotSaver.next()   // -> { filename, index, total, done }
//   playwright_screenshot({ selector: "#ss-img", savePng: true, downloadsDir: "<dir>", name: "<filename_stem>" })
// 4. Repeat until done === true
// 5. Cleanup:
window.ScreenshotSaver.destroy()
```

After all screenshots are saved, rename to strip Playwright's timestamp suffix:

```powershell
Get-ChildItem -Path "<output_dir>" -Filter "change_*-202*Z.png" | ForEach-Object {
    $newName = $_.Name -replace '-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d+Z', ''
    Rename-Item $_.FullName $newName
}
```

### References

- [Slide detection workflow](references/slide_detection.md) — full usage guide with parameters, output format, LLM enrichment, and known limitations
- [scripts/slide-detector.js](scripts/slide-detector.js) — the detection script
- [scripts/screenshot-saver.js](scripts/screenshot-saver.js) — overlay-based screenshot capture
- [scripts/resolve-drive-item.js](scripts/resolve-drive-item.js) — driveId/itemId resolution

---

## Scripts Reference

| Script | Purpose | Key API |
|--------|---------|---------|
| [`slide-detector.js`](scripts/slide-detector.js) | Detect visual transitions in video | `SlideDetector.run(opts)`, `.progress`, `.abort()` |
| [`screenshot-saver.js`](scripts/screenshot-saver.js) | Display and capture transition PNGs | `ScreenshotSaver.init()`, `.next()`, `.showTransition(i)`, `.destroy()` |
| [`resolve-drive-item.js`](scripts/resolve-drive-item.js) | Extract driveId/itemId from Stream page | `ResolveDriveItem.run()` |
