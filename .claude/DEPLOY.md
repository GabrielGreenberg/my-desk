# Deployment Setup

## Stack
- **Hosting**: Vercel (auto-deploys from GitHub)
- **Repo**: https://github.com/GabrielGreenberg/my-desk.git (branch: `main`)
- **Framework**: Static site (no build step) with Python serverless functions

## How it works
- `vercel.json` sets `outputDirectory: "."` and `buildCommand: ""` (no build)
- Serverless functions live in `api/` (voice.py, notion.py)
- Pushing to `main` triggers auto-deploy on Vercel

## Service Worker (sw.js)
- Pre-caches app shell assets (HTML, icons, manifest, Quill CSS/JS)
- **Cache-first** for static assets, **network-first** for HTML
- API calls are never cached
- **IMPORTANT**: When updating cached assets (icons, CSS, etc.), you MUST bump the `CACHE_NAME` version string (e.g. `my-desk-v3` → `my-desk-v4`) or Android/iOS will serve stale files indefinitely

## Icons
- Source: `leaflogo.png` (1336x1336)
- iOS: `apple-touch-icon.png` (180x180)
- Standard: `icon-192.png`, `icon-512.png`, `icon-1024.png`
- Android maskable: `android-icon-maskable-192.png`, `android-icon-maskable-512.png`
- Android standard: `android-icon-{48,72,96,144,192}.png`
- Manifest: `manifest.json` references all icons with correct `purpose` fields

## Environment
- `.env` holds `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `NOTION_TOKEN` (gitignored)
- `server.py` is for local dev only (not deployed)
- Vercel CLI is NOT installed locally; deploys happen via GitHub integration
