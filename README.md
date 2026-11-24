# TORQUENAUT Automation v4

Creates a 9:16 automotive video draft using Gemini for the script, Wikimedia Commons still images (with attribution), Edge TTS Hindi male neural voice, FFmpeg motion effects, and styled subtitles.

Required GitHub Actions secret: `GEMINI_API_KEY`.
Optional repository variable: `GEMINI_MODEL` (defaults to `gemini-3.5-flash-lite`; use a model enabled for your Google AI Studio project).

Run with GitHub Actions. The output artifact includes MP4, MP3 voiceover, SRT captions, content JSON, posting copy, and image attribution.

Note: visuals are animated still images, not generated live-action video clips. Review facts, image licenses, pronunciation and quality before publishing. No automatic social publishing is included.
