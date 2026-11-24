# TORQUENAUT Automation Starter

A starter cloud workflow for producing draft automotive vertical videos. It researches/generates a Hinglish script with Gemini, retrieves Pexels stock clips, creates Hindi TTS with Edge TTS, and renders an MP4 with FFmpeg. It does **not** upload/publish to social accounts.

## Required secrets (GitHub repository → Settings → Secrets and variables → Actions)
- `GEMINI_API_KEY` — Google AI Studio API key
- `PEXELS_API_KEY` — Pexels API key

## Setup from Android
1. Create a GitHub account and a new repository named `torquenaut-factory`.
2. Upload the contents of this folder to the repository (including `.github/workflows/daily.yml`).
3. Add the two secrets listed above.
4. Open the repository's **Actions** tab, select **TORQUENAUT Video Draft**, and tap **Run workflow**.
5. When it finishes, open the run and download the artifact `torquenaut-video-draft`.

The workflow is scheduled at 02:30 and 13:30 UTC (08:00 and 19:00 India time). Schedule may be delayed by GitHub. Manual runs are also supported.

## Notes
- Uses stock footage and a generated voice; outputs a draft, not guaranteed viral content.
- Free service quotas/terms may change. Avoid claiming free lifetime use.
- Check all facts, licenses, and rendered video before publishing.
