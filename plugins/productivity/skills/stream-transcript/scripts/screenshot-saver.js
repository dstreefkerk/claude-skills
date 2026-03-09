/**
 * Screenshot Saver for Slide Transition Detection
 *
 * Runs inside a Playwright browser context via playwright_evaluate.
 * Manages a full-screen overlay that displays transition screenshots
 * one at a time, so Playwright's playwright_screenshot can capture
 * each as a clean PNG file.
 *
 * Usage (from playwright_evaluate):
 *   // 1. Inject this script after slide detection is complete
 *   // 2. Initialize (reads from window._sdScreenshots or window._result):
 *   window.ScreenshotSaver.init()
 *   // 3. Loop: advance and screenshot
 *   window.ScreenshotSaver.next()   // -> { filename, index, total, done }
 *   //   then: playwright_screenshot({ selector: "#ss-img", savePng: true, ... })
 *   // 4. Repeat until done === true
 *   // 5. Cleanup:
 *   window.ScreenshotSaver.destroy()
 *
 * All methods return JSON strings for clean playwright_evaluate usage.
 */
(() => {
  'use strict';

  let _transitions = null;
  let _currentIndex = -1;
  let _overlay = null;
  let _img = null;

  function _getTransitions() {
    // Prefer the compact screenshot array stored by the scan step
    if (window._sdScreenshots && Array.isArray(window._sdScreenshots)) {
      return window._sdScreenshots;
    }
    // Fall back to the full result manifest
    if (window._result && Array.isArray(window._result.transitions)) {
      return window._result.transitions;
    }
    return null;
  }

  function _createOverlay() {
    _overlay = document.createElement('div');
    _overlay.id = 'ss-overlay';
    _overlay.style.cssText =
      'position:fixed;top:0;left:0;width:100vw;height:100vh;' +
      'z-index:99999;background:black;display:flex;' +
      'align-items:center;justify-content:center;';
    _img = document.createElement('img');
    _img.id = 'ss-img';
    _img.style.cssText = 'max-width:100%;max-height:100%;object-fit:contain;';
    _overlay.appendChild(_img);
    document.body.appendChild(_overlay);
  }

  function _showImage(dataUrl) {
    return new Promise((resolve) => {
      _img.onload = () => resolve();
      _img.onerror = () => resolve(); // resolve anyway to avoid hanging
      _img.src = dataUrl;
      // Safety timeout for very large images
      setTimeout(resolve, 3000);
    });
  }

  // ── Public API ──────────────────────────────────────────────────────

  function init() {
    _transitions = _getTransitions();
    if (!_transitions || _transitions.length === 0) {
      return JSON.stringify({ error: 'No transition data found. Run slide detection first.' });
    }
    _currentIndex = -1;
    _createOverlay();
    return JSON.stringify({
      status: 'ready',
      total: _transitions.length
    });
  }

  async function next() {
    if (!_transitions) {
      return JSON.stringify({ error: 'Not initialized. Call init() first.' });
    }
    _currentIndex++;
    if (_currentIndex >= _transitions.length) {
      return JSON.stringify({ done: true, index: _currentIndex, total: _transitions.length });
    }
    const t = _transitions[_currentIndex];
    const dataUrl = t.screenshotDataUrl;
    if (!dataUrl) {
      return JSON.stringify({ error: `No screenshotDataUrl at index ${_currentIndex}` });
    }
    await _showImage(dataUrl);
    return JSON.stringify({
      done: false,
      filename: t.screenshotFile,
      index: _currentIndex,
      total: _transitions.length
    });
  }

  async function showTransition(idx) {
    if (!_transitions) {
      return JSON.stringify({ error: 'Not initialized. Call init() first.' });
    }
    if (idx < 0 || idx >= _transitions.length) {
      return JSON.stringify({ error: `Index ${idx} out of range (0-${_transitions.length - 1})` });
    }
    _currentIndex = idx;
    const t = _transitions[idx];
    await _showImage(t.screenshotDataUrl);
    return JSON.stringify({
      done: false,
      filename: t.screenshotFile,
      index: idx,
      total: _transitions.length
    });
  }

  function destroy() {
    if (_overlay) {
      _overlay.remove();
      _overlay = null;
      _img = null;
    }
    _transitions = null;
    _currentIndex = -1;
    return JSON.stringify({ status: 'destroyed' });
  }

  window.ScreenshotSaver = { init, next, showTransition, destroy };

  console.log('[ScreenshotSaver] Loaded. Call window.ScreenshotSaver.init() to start.');
})();
