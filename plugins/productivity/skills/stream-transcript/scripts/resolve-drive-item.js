/**
 * Drive Item Resolver for Microsoft Stream Videos
 *
 * Runs inside a Playwright browser context via playwright_evaluate.
 * Extracts the driveId and itemId from a Stream/SharePoint video page
 * using multiple resolution strategies in order of reliability.
 *
 * Usage (from playwright_evaluate):
 *   // 1. Navigate to the Stream video page and authenticate
 *   // 2. Inject this script
 *   // 3. Resolve:
 *   await window.ResolveDriveItem.run()
 *   // Returns JSON: { driveId, itemId, filePath, method }
 *
 * Resolution order:
 *   1. Sharing/encoding API (most reliable)
 *   2. Script tag search (drives/xxx/items/xxx pattern)
 *   3. SharePoint REST API (GetFileByServerRelativeUrl)
 *   4. Page context / React hydration data
 */
(() => {
  'use strict';

  function _getFilePath() {
    const params = new URLSearchParams(window.location.search);
    return params.get('id') || null;
  }

  // ── Method 1: Sharing/encoding API ────────────────────────────────
  // Encode the file URL as a share token, then resolve via Graph-style endpoint.
  // This is the most reliable method — works even when page JS hasn't fully loaded.

  async function _trySharingApi(filePath) {
    try {
      const fileUrl = window.location.origin + filePath;
      const encoded = 'u!' + btoa(fileUrl)
        .replace(/=/g, '')
        .replace(/\//g, '_')
        .replace(/\+/g, '-');
      const r = await fetch(`/_api/v2.1/shares/${encoded}/driveItem`, {
        credentials: 'include',
        headers: { 'Accept': 'application/json' }
      });
      if (!r.ok) return null;
      const item = await r.json();
      const driveId = item.parentReference?.driveId;
      const itemId = item.id;
      if (driveId && itemId) {
        return { driveId, itemId, method: 'sharing-api' };
      }
    } catch (e) {
      console.log('[ResolveDriveItem] Sharing API failed:', e.message);
    }
    return null;
  }

  // ── Method 2: Script tag search ───────────────────────────────────
  // Scan inline <script> tags for drives/xxx/items/xxx patterns.

  function _tryScriptTagSearch() {
    try {
      let driveId = null, itemId = null;
      const scripts = document.querySelectorAll('script');
      for (const s of scripts) {
        const text = s.textContent;
        if (!text) continue;
        const driveMatch = text.match(/drives\/([A-Za-z0-9!_-]+)/);
        const itemMatch = text.match(/items\/([A-Za-z0-9!_-]+)/);
        if (driveMatch && !driveId) driveId = driveMatch[1];
        if (itemMatch && !itemId) itemId = itemMatch[1];
        if (driveId && itemId) {
          return { driveId, itemId, method: 'script-tag-search' };
        }
      }
    } catch (e) {
      console.log('[ResolveDriveItem] Script tag search failed:', e.message);
    }
    return null;
  }

  // ── Method 3: SharePoint REST API ─────────────────────────────────
  // Use GetFileByServerRelativeUrl to get file metadata, then resolve
  // the driveId via the list/site GUIDs.

  async function _trySharePointRest(filePath) {
    try {
      const r = await fetch(
        `/_api/web/GetFileByServerRelativeUrl('${filePath}')?$select=UniqueId,ListId,SiteId,WebId,ListItemAllFields/Id&$expand=ListItemAllFields`,
        { credentials: 'include', headers: { 'Accept': 'application/json;odata=verbose' } }
      );
      if (!r.ok) return null;
      const data = await r.json();
      const fileInfo = data.d;
      // The driveId can sometimes be constructed from list metadata,
      // but this method alone doesn't reliably give us both IDs.
      // Return what we have for the caller to combine with other methods.
      if (fileInfo) {
        return {
          uniqueId: fileInfo.UniqueId,
          listId: fileInfo.ListId,
          siteId: fileInfo.SiteId,
          webId: fileInfo.WebId,
          method: 'sharepoint-rest'
        };
      }
    } catch (e) {
      console.log('[ResolveDriveItem] SharePoint REST failed:', e.message);
    }
    return null;
  }

  // ── Method 4: Page context / hydration data ───────────────────────
  // Look for _spPageContextInfo or embedded JSON with drive references.

  function _tryPageContext() {
    try {
      const ctx = window._spPageContextInfo;
      if (ctx) {
        // Page context may contain list/site IDs but rarely driveId directly.
        // Still useful as supplementary data.
        return {
          siteId: ctx.siteId,
          webId: ctx.webId,
          listId: ctx.listId,
          method: 'page-context'
        };
      }
    } catch (e) {
      console.log('[ResolveDriveItem] Page context failed:', e.message);
    }
    return null;
  }

  // ── Main Entry Point ──────────────────────────────────────────────

  async function run() {
    const filePath = _getFilePath();
    const result = { driveId: null, itemId: null, filePath, method: null };

    // Method 1: Sharing API (most reliable)
    if (filePath) {
      const sharing = await _trySharingApi(filePath);
      if (sharing && sharing.driveId && sharing.itemId) {
        return JSON.stringify({ ...result, ...sharing });
      }
    }

    // Method 2: Script tag search
    const scriptResult = _tryScriptTagSearch();
    if (scriptResult && scriptResult.driveId && scriptResult.itemId) {
      return JSON.stringify({ ...result, ...scriptResult });
    }

    // Method 3: SharePoint REST API
    if (filePath) {
      const restResult = await _trySharePointRest(filePath);
      if (restResult) {
        // REST doesn't give driveId/itemId directly, log what we got
        console.log('[ResolveDriveItem] REST partial result:', restResult);
      }
    }

    // Method 4: Page context
    const ctxResult = _tryPageContext();
    if (ctxResult) {
      console.log('[ResolveDriveItem] Page context partial result:', ctxResult);
    }

    // If we got partial results from methods 2-4 but not a complete pair,
    // return what we have
    return JSON.stringify({
      ...result,
      error: 'Could not resolve both driveId and itemId. Check console for partial results.',
      method: 'none'
    });
  }

  window.ResolveDriveItem = { run };

  console.log('[ResolveDriveItem] Loaded. Call window.ResolveDriveItem.run() to resolve.');
})();
