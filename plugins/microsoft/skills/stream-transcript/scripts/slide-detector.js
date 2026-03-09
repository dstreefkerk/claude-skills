/**
 * Slide Transition Detector for Microsoft Stream Videos
 *
 * Runs inside a Playwright browser context via playwright_evaluate.
 * Detects visual changes in Teams meeting recordings by comparing
 * block-based color hashes of video frames at regular intervals.
 *
 * Uses a fast single-pass approach: scan at the configured interval,
 * capture a full-resolution screenshot immediately when a change is
 * detected, and return the manifest with base64 PNG data URLs.
 *
 * Usage (from playwright_evaluate):
 *   // 1. Inject this script
 *   // 2. Start the scan:
 *   const result = await window.SlideDetector.run({
 *     coarseInterval: 60,   // seconds between samples (default 60)
 *     threshold: 10,        // min diff to count as change (default 10)
 *     captureRegion: { x: 0, y: 0, w: 0.75, h: 1.0 }  // left 75%
 *   });
 *
 * For long videos, start async and poll progress:
 *   window.SlideDetector.run(opts).then(r => { window._result = r; });
 *   // Poll: window.SlideDetector.progress  (0-100)
 *   // Abort: window.SlideDetector.abort()
 *
 * Returns a manifest object with base64 PNG data URLs for each transition.
 * The caller (Claude) decodes and saves PNGs to disk.
 */
(() => {
  'use strict';

  // ── Internal state ──────────────────────────────────────────────────
  let _aborted = false;
  let _progress = 0;

  // ── Helpers ─────────────────────────────────────────────────────────

  function _seekAndWait(video, time) {
    return new Promise((resolve) => {
      if (_aborted) { resolve(); return; }
      const onSeeked = () => {
        video.removeEventListener('seeked', onSeeked);
        setTimeout(resolve, 60);
      };
      video.addEventListener('seeked', onSeeked);
      video.currentTime = time;
      // Safety timeout in case seeked never fires
      setTimeout(() => {
        video.removeEventListener('seeked', onSeeked);
        resolve();
      }, 2000);
    });
  }

  function _hashFrame(video, region, canvas, ctx) {
    const vw = video.videoWidth;
    const vh = video.videoHeight;

    // Draw the capture region downscaled to 240x135
    canvas.width = 240;
    canvas.height = 135;
    ctx.drawImage(video,
      Math.round(region.x * vw), Math.round(region.y * vh),
      Math.round(region.w * vw), Math.round(region.h * vh),
      0, 0, 240, 135);

    // Compute 8x6 block hash (144 values: avgR, avgG, avgB per block)
    const { data, width, height } = ctx.getImageData(0, 0, 240, 135);
    const cols = 8, rows = 6;
    const blockW = Math.floor(width / cols);
    const blockH = Math.floor(height / rows);
    const hash = [];

    for (let row = 0; row < rows; row++) {
      for (let col = 0; col < cols; col++) {
        let rSum = 0, gSum = 0, bSum = 0, count = 0;
        const startY = row * blockH;
        const startX = col * blockW;
        for (let y = startY; y < startY + blockH; y++) {
          for (let x = startX; x < startX + blockW; x++) {
            const i = (y * width + x) * 4;
            rSum += data[i];
            gSum += data[i + 1];
            bSum += data[i + 2];
            count++;
          }
        }
        hash.push(rSum / count, gSum / count, bSum / count);
      }
    }
    return hash;
  }

  function _compareHashes(h1, h2) {
    if (!h1 || !h2 || h1.length !== h2.length) return Infinity;
    let totalDiff = 0;
    for (let i = 0; i < h1.length; i++) {
      totalDiff += Math.abs(h1[i] - h2[i]);
    }
    return totalDiff / h1.length;
  }

  function _captureFullFrame(video, region) {
    const vw = video.videoWidth;
    const vh = video.videoHeight;
    const captureW = Math.round(region.w * vw);
    const captureH = Math.round(region.h * vh);
    const sx = Math.round(region.x * vw);
    const sy = Math.round(region.y * vh);

    const fullCanvas = document.createElement('canvas');
    fullCanvas.width = captureW;
    fullCanvas.height = captureH;
    const fullCtx = fullCanvas.getContext('2d');
    fullCtx.drawImage(video, sx, sy, captureW, captureH, 0, 0, captureW, captureH);
    return fullCanvas.toDataURL('image/png');
  }

  function _formatTimestamp(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  }

  function _formatFilename(index, seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `change_${String(index).padStart(3, '0')}_${m}m${s.toString().padStart(2, '0')}s.png`;
  }

  // ── Main Entry Point ────────────────────────────────────────────────

  async function run(options = {}) {
    _aborted = false;
    _progress = 0;

    const interval = options.coarseInterval || 60;
    const threshold = options.threshold || 10;
    const region = options.captureRegion || { x: 0, y: 0, w: 0.75, h: 1.0 };

    const video = document.querySelector('video');
    if (!video) throw new Error('No <video> element found on the page');

    // Ensure video is paused for seeking
    video.pause();

    // Verify canvas access
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 240;
    canvas.height = 135;
    try {
      ctx.drawImage(video, 0, 0, 240, 135);
      ctx.getImageData(0, 0, 1, 1);
    } catch (e) {
      throw new Error(
        'Cannot read video pixels. Ensure the video element has ' +
        'crossOrigin="anonymous" and the source allows CORS. Error: ' + e.message
      );
    }

    const duration = video.duration;
    if (!duration || !isFinite(duration)) {
      throw new Error('Video duration is not available. Is the video loaded?');
    }

    const totalSteps = Math.ceil(duration / interval);
    console.log(`[SlideDetector] Starting: duration=${Math.round(duration)}s, ` +
      `interval=${interval}s, ~${totalSteps} steps`);

    // ── Single-pass scan: hash + capture on change ──
    let prevHash = null;
    const transitions = [];
    let idx = 0;

    for (let t = 0; t <= duration; t += interval) {
      if (_aborted) throw new Error('Aborted');

      await _seekAndWait(video, t);
      const hash = _hashFrame(video, region, canvas, ctx);
      const diff = prevHash ? _compareHashes(prevHash, hash) : 0;

      if (diff >= threshold) {
        idx++;
        const dataUrl = _captureFullFrame(video, region);
        const confidence = diff >= 30 ? 'HIGH' : diff >= 15 ? 'MEDIUM' : 'LOW';

        transitions.push({
          index: idx,
          timestamp: Math.round(t),
          timestampFormatted: _formatTimestamp(t),
          confidence,
          diffScore: Math.round(diff * 100) / 100,
          screenshotFile: _formatFilename(idx, t),
          screenshotDataUrl: dataUrl
        });

        console.log(`[SlideDetector] #${idx} t=${_formatTimestamp(t)} ` +
          `diff=${diff.toFixed(1)} (${confidence})`);
      }

      prevHash = hash;
      _progress = Math.round(((t / interval) / totalSteps) * 100);
    }

    _progress = 100;

    const manifest = {
      videoUrl: window.location.href,
      videoDuration: Math.round(duration),
      scanDate: new Date().toISOString(),
      scanParams: { coarseInterval: interval, threshold },
      transitions
    };

    console.log(`[SlideDetector] Done. ${transitions.length} transitions found.`);
    return manifest;
  }

  // ── Public API ──────────────────────────────────────────────────────

  window.SlideDetector = {
    run,
    get progress() { return _progress; },
    abort() {
      _aborted = true;
      console.log('[SlideDetector] Abort requested');
    }
  };

  console.log('[SlideDetector] Loaded. Call window.SlideDetector.run(options) to start.');
})();
