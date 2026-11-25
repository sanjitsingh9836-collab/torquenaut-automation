# TORQUENAUT Automation v5

This update improves the image-fetching resilience:
- Searches Wikimedia Commons with multiple query phrases.
- Skips corrupt/unsupported images instead of stopping at the first failure.
- Uses a no-key Unsplash photo fallback if Commons returns fewer than 4 usable images.
- Tries two Hindi neural TTS voices.
- Produces vertical video, yellow bold outlined subtitles, and posting copy.

**Honest limitation:** this is a photo-based motion video (pan/zoom), not generative AI video footage. Publishing to YouTube/Instagram is not automated by this package.

## Installation
Run the existing GitHub updater workflow after uploading `torquenaut-automation-v5.zip` to the repository root and changing the updater's ZIP filename to v5.
