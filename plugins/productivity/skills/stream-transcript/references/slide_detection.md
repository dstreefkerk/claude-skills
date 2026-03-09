# Slide Transition Detection for Stream Videos

Detect visual changes (slide transitions, screen share changes, layout switches) in
Teams meeting recordings hosted on Microsoft Stream, and capture screenshots of each
distinct visual state.

## How It Works

The script `scripts/slide-detector.js` runs inside the Playwright browser context on
a Stream video page. It:

1. Pauses the video and seeks through it at regular intervals
2. Draws each frame to an offscreen canvas and computes an 8x6 block color hash
3. Compares consecutive hashes; when the mean per-channel diff exceeds the threshold, a transition is recorded
4. Captures a full-resolution PNG screenshot of the left 75% of the frame (where slides appear in Teams presenter mode)
5. Returns a JSON manifest with timestamps, confidence scores, and base64 PNG data URLs

## Teams Recording Layouts

Teams recordings have three distinct visual layouts:

| Layout | Description | Slide region |
|--------|-------------|-------------|
| **Presenter mode** | Shared content (slides/screen) fills left ~75%, webcam strip on right | `{x:0, y:0, w:0.75, h:1.0}` |
| **Screen share mode** | Browser/app share fills left ~75%, webcam strip on right | Same as above |
| **Gallery mode** | Webcam grid fills entire frame, no shared content | Full frame, but no slides to capture |

The default `captureRegion` of `{x:0, y:0, w:0.75, h:1.0}` crops to the slide area,
excluding the webcam strip. Adjust if the video layout differs.

## Usage

### Step 1: Navigate to the Stream video

The browser must already be authenticated to SharePoint (use the transcript skill's
auth flow if needed).

```text
playwright_navigate({ url: streamVideoUrl, headless: false, timeout: 90000 })
```

Wait for the video to load and start playing briefly so frames are available.

### Step 2: Inject the script

Read `scripts/slide-detector.js` and inject via `playwright_evaluate`.

### Step 3: Start the scan

```javascript
window._sdResult = null;
window._sdDone = false;
window.SlideDetector.run({
  coarseInterval: 60,   // sample every 60 seconds
  threshold: 10,        // minimum diff score to count as a change
  captureRegion: { x: 0, y: 0, w: 0.75, h: 1.0 }
}).then(result => {
  window._sdScreenshots = result.transitions.map(t => ({
    index: t.index,
    screenshotFile: t.screenshotFile,
    screenshotDataUrl: t.screenshotDataUrl
  }));
  const manifest = JSON.parse(JSON.stringify(result));
  manifest.transitions.forEach(t => { t.screenshotDataUrl = '[stored]'; });
  window._sdResult = manifest;
  window._sdDone = true;
});
```

### Step 4: Poll for progress

```javascript
JSON.stringify({
  progress: window.SlideDetector.progress,  // 0-100
  done: window._sdDone,
  error: window._sdError
})
```

For an 84-minute video at 60s intervals, the scan takes ~8 minutes.

### Step 5: Retrieve results

The manifest (without large data URLs) is at `window._sdResult`. Individual
screenshot base64 data is at `window._sdScreenshots[i].screenshotDataUrl`.

### Step 6: Save screenshots to disk

Inject `scripts/screenshot-saver.js` and use the overlay + Playwright screenshot approach.

#### 6a. Initialize the saver

```javascript
// Inject screenshot-saver.js via playwright_evaluate, then:
window.ScreenshotSaver.init()
// Returns: { status: "ready", total: N }
```

The saver auto-detects data from `window._sdScreenshots` (preferred) or `window._result.transitions`.

#### 6b. Loop: advance and capture

For each transition, make two tool calls:

1. `playwright_evaluate`: `window.ScreenshotSaver.next()`
   Returns `{ filename, index, total, done }`. Stop when `done === true`.
2. `playwright_screenshot` with:
   - `selector: "#ss-img"` (the overlay image element)
   - `savePng: true`
   - `downloadsDir: "<output_dir>"`
   - `name: "<filename_without_.png_extension>"`

To jump to a specific index instead: `window.ScreenshotSaver.showTransition(idx)`

#### 6c. Cleanup

```javascript
window.ScreenshotSaver.destroy()
// Returns: { status: "destroyed" }
```

#### 6d. Rename files (strip Playwright timestamp suffix)

Playwright appends a timestamp to saved PNGs (e.g. `change_001_1m00s-2026-02-12T10-30-00-123Z.png`).
Strip it with PowerShell:

```powershell
Get-ChildItem -Path "<output_dir>" -Filter "change_*-202*Z.png" | ForEach-Object {
    $newName = $_.Name -replace '-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d+Z', ''
    Rename-Item $_.FullName $newName
}
```

The regex `-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}-\d+Z` matches the ISO timestamp suffix that Playwright adds.

### Why not other save methods?

These approaches were tried and failed. Documenting to avoid re-attempting them.

| Method | Why it fails |
|--------|-------------|
| **Browser downloads** (`a.click()` with `download` attr) | Playwright's `downloadsDir` setting only applies to `playwright_screenshot`, not browser-initiated downloads. Files go to the system default Downloads folder with no control over path. |
| **HTTP server** (serve base64 via local HTTP) | Requires spawning a server process. Overly complex for this use case and runs into CORS issues within the Playwright browser context. |
| **Base64 extraction + file write** | Each screenshot is ~500KB-2MB of base64 text. Extracting via `playwright_evaluate` hits return-value size limits and floods the conversation context. |
| **Canvas `toBlob()` + clipboard** | No reliable way to transfer binary data from the browser context to the local filesystem via clipboard. |
| **Python `base64.b64decode()`** | Same problem as base64 extraction -- getting the data out of the browser is the bottleneck, not the decoding. |

The **Playwright overlay + `playwright_screenshot`** approach works because it keeps data inside the browser and uses Playwright's native file-saving capability.

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `coarseInterval` | `60` | Seconds between frame samples. Lower = more precise but slower. 60s works well for most meetings. |
| `threshold` | `10` | Minimum mean per-channel diff to register as a change. 10 catches most slide transitions. |
| `captureRegion` | `{x:0, y:0, w:0.75, h:1.0}` | Fractional region of the video frame to analyze and capture. Default crops to the left 75% (slide area). |

## Confidence Levels

| Level | Diff Score | Typical cause |
|-------|-----------|---------------|
| **HIGH** | >= 30 | Slide change, layout switch (gallery <-> presenter), screen share start/stop |
| **MEDIUM** | 15-30 | Slide with partial changes, scrolling content, webcam movement with slides |
| **LOW** | 10-15 | Minor visual changes, webcam-only movement, subtle slide updates |

## Hash Algorithm

- Downscale captured region to 240x135 pixels
- Divide into 8 columns x 6 rows = 48 blocks (30x22 pixels each)
- Compute average R, G, B per block -> 144-element array
- Compare: mean absolute difference across all 144 elements
- Threshold of 10 reliably separates real content changes from noise

## Step 7: LLM Post-Processing (Recommended)

After saving screenshots to disk, use Claude's vision capabilities to enrich and
validate the results. Read each PNG file with the Read tool and ask Claude to analyze it.

### What the LLM adds to each transition

| Field | Description |
|-------|-------------|
| `slideTitle` | The heading or title text visible on the slide |
| `slideDescription` | Brief description of the slide content (bullet points, diagrams, tables, etc.) |
| `contentType` | One of: `slide`, `screen-share`, `gallery-view`, `transition-artifact`, `duplicate` |
| `isContent` | `true` if meaningful visual content is present, `false` for webcam-only or artifacts |
| `duplicateOf` | Index of an earlier transition if this shows the same slide/content, `null` otherwise |

### Workflow

Use **sub-agents** (Task tool with `subagent_type: "general-purpose"`) to process
screenshots in parallel batches. This avoids loading all images into the main
conversation context. Launch one sub-agent per batch of ~5 screenshots.

Each sub-agent receives:

- The file paths of its assigned screenshots
- The manifest metadata for those transitions (timestamp, confidence, diffScore)
- The list of slide titles/descriptions already identified by prior sub-agents (for duplicate detection)

Process in priority order to minimize cost:

1. **LOW confidence first** (diff 10-15): Most likely to be false positives (webcam noise).
   Read each PNG and classify. Drop any where `isContent` is false.
2. **MEDIUM confidence** (diff 15-30): May be real slide changes or scrolling content.
   Read each PNG, describe, and check for duplicates against prior slides.
3. **HIGH confidence** (diff >= 30): Almost always real transitions. Read each PNG and
   add title/description. Check for duplicates only against adjacent transitions.

### Prompt template for each screenshot

When reading a screenshot PNG, use reasoning like:

```text
Look at this screenshot captured from a Teams meeting recording at timestamp {timestampFormatted}.
The visual change detection scored it as {confidence} confidence (diff: {diffScore}).

1. What is the content type? (presentation slide / screen share / webcam gallery / transition artifact / duplicate)
2. If it's a slide or screen share: what is the title and a brief description of the content?
3. Does this appear to be the same content as any previously described slide?
```

### Enhanced output format

After LLM processing, the manifest transitions gain additional fields:

```json
{
  "index": 6,
  "timestamp": 1680,
  "timestampFormatted": "28:00",
  "confidence": "HIGH",
  "diffScore": 58.2,
  "screenshotFile": "change_006_28m00s.png",
  "contentType": "slide",
  "isContent": true,
  "slideTitle": "What events and data do we need to collect?",
  "slideDescription": "Bullet point about event sources covering required areas of concern. Matrix table showing source categories (Scanners, Infrastructure, Endpoint, Communications, Authentication, Gateways, Cloud Services) with columns for Detective Sources, Non-detective Sources, Limited value Sources, Enforcement Capability, Volume, and Source Impact.",
  "duplicateOf": null
}
```

### Filtering the final output

After LLM processing, produce a clean manifest by:

1. Removing entries where `isContent` is `false` (webcam-only frames)
2. Removing entries where `contentType` is `transition-artifact` (blurry mid-transitions)
3. Marking `duplicateOf` entries but keeping them (they show when the presenter returned to a slide)
4. Renumbering the remaining transitions sequentially

This typically reduces 20+ raw detections down to 10-15 distinct slides with accurate titles and descriptions.

## Known Limitations

- **Stream session timeout**: The Stream playback session expires after ~15-20 minutes of seeking. Use `coarseInterval: 60` (not 30) to stay within the timeout window.
- **Timestamp precision**: At 60s intervals, detected timestamps are accurate to within ~60 seconds of the actual transition.
- **Gallery mode noise**: Webcam-only segments produce LOW-confidence detections from people moving. Filter by confidence if needed.
- **Mid-transition captures**: Screenshots are taken at the sample point, which may occasionally catch a mid-transition frame. Use a slightly later timestamp if the screenshot looks blurry.

## Output Format

```json
{
  "videoUrl": "https://...",
  "videoDuration": 5046,
  "scanDate": "2026-02-12T...",
  "scanParams": { "coarseInterval": 60, "threshold": 10 },
  "transitions": [
    {
      "index": 1,
      "timestamp": 60,
      "timestampFormatted": "1:00",
      "confidence": "HIGH",
      "diffScore": 116.68,
      "screenshotFile": "change_001_1m00s.png",
      "screenshotDataUrl": "data:image/png;base64,..."
    }
  ]
}
```
