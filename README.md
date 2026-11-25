# TORQUENAUT Automation

Automated short-form automotive video generator for **TORQUENAUT** and the **MACHINE KA RAAZ** series.

## What it does
- Generates a short Hinglish script with Gemini (falls back to a built-in script if the API call fails).
- Searches Wikimedia Commons using topic-specific phrases and downloads vertical images; uses Unsplash fallback images if needed.
- Produces a Hindi/Hinglish voice track using Edge TTS, with Google TTS fallback.
- Builds a 9:16 MP4 with subtle image movement and burned-in yellow outlined subtitles.
- Writes title, topic, narration, posting caption, and subtitle files into `output/`.
- GitHub Actions scheduled workflow runs twice daily (08:00 and 19:00 IST).

## Current limitations
This produces photo-based videos with motion—not generated cinematic video clips. Topic-relevance of search images is not guaranteed, so review videos before publishing. Uploading/scheduling to YouTube or Instagram is not yet connected.

## Required repository secret
Set `GEMINI_API_KEY` in repository Settings → Secrets and variables → Actions.

## Run manually
GitHub → Actions → **TorqueNaut Video Factory** → **Run workflow**.

The workflow uploads generated files as a downloadable artifact for 7 days.
