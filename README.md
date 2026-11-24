# TORQUENAUT Automated Video Draft Factory

This cloud workflow generates a short vertical automotive educational draft: Gemini script, Hindi TTS, Wikimedia Commons still images with slow motion, captions, MP4, and post text. It does **not** automatically publish to Instagram or YouTube.

## Required GitHub secret
- `GEMINI_API_KEY` — Google AI Studio key

No Pexels key is required. Image retrieval uses the Wikimedia Commons API (no key) and records image attribution/license metadata in `output/image_credits.json`. Wikimedia results may vary; check credits and licenses before publishing.

## Run from mobile
1. Upload/replace `factory.py`, `requirements.txt`, `README.md`, and `.github/workflows/daily.yml` in your repository.
2. Confirm repository Settings → Secrets and variables → Actions has `GEMINI_API_KEY`.
3. Open Actions → **TORQUENAUT Video Factory** → Run workflow → Run workflow.
4. When complete, open the run and download the artifact `torquenaut-video-draft`.

Schedule: 02:30 and 13:30 UTC (08:00 and 19:00 India time). GitHub scheduled jobs can be delayed; manual runs are available. This is a draft maker, not guaranteed daily uptime, viral results, or lifetime-free service. Inspect factual notes and image license credits before publishing.
