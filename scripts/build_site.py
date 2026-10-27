#!/usr/bin/env python3
"""Rebuild index.html (archive) and feed.xml (podcast RSS) from issues/*.html.

Usage: python3 scripts/build_site.py
Each issue page must carry <meta name="fn-date">, <meta name="fn-headline">,
<meta name="fn-summary"> and a filled <script id="audio-meta"> block.
"""
import datetime, glob, html, json, os, re
from email.utils import format_datetime

SITE = "https://wangbard.github.io/frontier_notes/"
TITLE = "Frontier Notes"
DESC = ("A weekly briefing on AI-driven advances in mathematics and cryptography, "
        "with the best of physics and chemistry. Every claim carries a trust label.")
AUTHOR = "wangbard"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def meta(page, name):
    m = re.search(r'<meta name="%s" content="([^"]*)">' % name, page)
    return html.unescape(m.group(1)) if m else ""


def load_issues():
    issues = []
    for path in glob.glob(os.path.join(ROOT, "issues", "*.html")):
        page = open(path, encoding="utf-8").read()
        date = meta(page, "fn-date")
        if not date:
            continue
        am = re.search(r'id="audio-meta">(.*?)</script>', page, re.S)
        dur = 0
        if am:
            try:
                dur = float(json.loads(am.group(1)).get("dur") or 0)
            except ValueError:
                pass
        mp3 = os.path.join(ROOT, "audio", date + ".mp3")
        issues.append({
            "date": date, "headline": meta(page, "fn-headline"), "summary": meta(page, "fn-summary"),
            "page": "issues/%s.html" % date, "dur": dur,
            "mp3": "audio/%s.mp3" % date if os.path.exists(mp3) else "",
            "bytes": os.path.getsize(mp3) if os.path.exists(mp3) else 0,
        })
    return sorted(issues, key=lambda i: i["date"], reverse=True)


def nice_date(d):
    return datetime.date.fromisoformat(d).strftime("%A %-d %B %Y")


def hms(s):
    s = int(round(s))
    return "%02d:%02d:%02d" % (s // 3600, s % 3600 // 60, s % 60)


def build_index(issues):
    rows = []
    for n, i in enumerate(issues):
        mins = " About %d min to listen." % max(1, round(i["dur"] / 60)) if i["dur"] else ""
        rows.append(
            '<li><a class="item" href="%s"><span class="d">%s</span><span class="h">%s</span>'
            '<span class="s">%s%s</span></a></li>' % (
                i["page"], nice_date(i["date"]), html.escape(i["headline"]),
                html.escape(i["summary"]), mins))
    body = "\n".join(rows) or "<li>No issues yet.</li>"
    tpl = open(os.path.join(ROOT, "scripts", "index_template.html"), encoding="utf-8").read()
    out = tpl.replace("{{ISSUES}}", body).replace("{{FEED}}", SITE + "feed.xml")
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(out)


def build_feed(issues):
    items = []
    for i in issues:
        if not i["mp3"]:
            continue
        when = datetime.datetime.fromisoformat(i["date"] + "T07:00:00+00:00")
        items.append("""    <item>
      <title>%s</title>
      <description>%s</description>
      <link>%s</link>
      <guid isPermaLink="false">frontier-notes-%s</guid>
      <pubDate>%s</pubDate>
      <enclosure url="%s" length="%d" type="audio/mpeg"/>
      <itunes:duration>%s</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""" % (html.escape(i["headline"]), html.escape(i["summary"] + " Full text: " + SITE + i["page"]),
                 SITE + i["page"], i["date"], format_datetime(when), SITE + i["mp3"], i["bytes"], hms(i["dur"])))
    feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>%s</title>
    <link>%s</link>
    <atom:link href="%sfeed.xml" rel="self" type="application/rss+xml"/>
    <description>%s</description>
    <language>en</language>
    <itunes:author>%s</itunes:author>
    <itunes:category text="Science"/>
    <itunes:explicit>false</itunes:explicit>
%s
  </channel>
</rss>
""" % (TITLE, SITE, SITE, html.escape(DESC), AUTHOR, "\n".join(items))
    open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8").write(feed)


if __name__ == "__main__":
    issues = load_issues()
    build_index(issues)
    build_feed(issues)
    print("Built index.html and feed.xml with %d issues" % len(issues))
