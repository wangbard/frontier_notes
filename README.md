# Frontier Notes

A weekly briefing on AI-driven advances in mathematics and cryptography, with the best of physics and chemistry. Each issue has a 10-minute written version and a 3-minute audio version, and every claim carries a label saying how far it has been verified.

- Read: https://wangbard.github.io/frontier_notes/
- Podcast feed: https://wangbard.github.io/frontier_notes/feed.xml

## How it works
A scheduled Claude task follows `TASK.md` each week: it researches, writes `issues/YYYY-MM-DD.html`, generates audio with `scripts/make_audio.py` (Piper, voice `en-us-lessac-medium`), rebuilds the archive and feed with `scripts/build_site.py`, and pushes. GitHub Actions merge the branch and deploy the site.
