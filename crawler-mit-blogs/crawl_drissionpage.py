"""Crawl https://mitadmissions.org/blogs/ with DrissionPage and save a CSV.

Columns: Title | Author | Comment Count | Time | Article Content | Images In Article

Key detail: the comment count on the listing page is rendered client-side by
Disqus count.js (the anchor is empty in the raw HTML), so a real browser is
required. Comment counts are read from the listing page; article bodies and
images come from each article page.

DrissionPage drives the locally installed Chrome/Edge (no extra browser download).

Usage:
    python crawl_drissionpage.py --pages 1 --max 0 --out mit_blogs_drissionpage.csv
"""

import argparse
import csv
import re
import time

from DrissionPage import ChromiumOptions, ChromiumPage

BASE_URL = "https://mitadmissions.org/blogs/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DISQUS_LINK_CSS = "a[href$='#disqus_thread']"


def make_browser(proxy=None):
    """Launch an isolated headless Chrome; fall back to Edge if needed."""
    co = ChromiumOptions()
    co.headless(True)
    co.auto_port()  # isolated instance, does not touch the user's own Chrome
    co.set_user_agent(USER_AGENT)
    if proxy:
        co.set_proxy(proxy)
    try:
        return ChromiumPage(co), "chrome"
    except Exception as e:
        print(f"[warn] Chrome not available ({e}); trying Edge")
        co.set_browser_path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
        return ChromiumPage(co), "edge"


def wait_for_comment_counts(page, timeout_s=12):
    """Poll until Disqus count.js has filled every comment-count anchor."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        texts = [e.text.strip() for e in page.eles(DISQUS_LINK_CSS)]
        if texts and all(texts):
            return True
        time.sleep(0.5)
    return False


def parse_listing(page):
    """Extract one row per article card on the listing page."""
    rows = []
    for card in page.eles("css:article.tease"):
        link = card.ele("css:a.post-tease__h__link")
        if link is None:
            continue
        title_el = card.ele("css:.post-tease__title")
        author_el = card.ele("css:.post-tease__meta-item--author a")
        date_el = card.ele("css:.tease__meta-item--date")
        count_el = card.ele(DISQUS_LINK_CSS)
        rows.append({
            "title": title_el.text.strip() if title_el else link.text.strip(),
            "author": author_el.text.strip() if author_el else "",
            "time": date_el.text.strip() if date_el else "",
            "commentText": count_el.text.strip() if count_el else "",
            "url": link.attr("href"),
        })
    return rows


def parse_article(page, url):
    """Fetch one article page and return (content_text, images_joined)."""
    # The Disqus embed request hangs on networks where Disqus is unreachable,
    # which would stall the page "load" event for ~20s. The DOM is ready in a
    # few seconds, so cap the wait and query elements directly afterwards.
    page.get(url, timeout=12)
    body = page.ele("css:.article__body", timeout=30)
    if body is None:
        return "", ""
    content = body.text.strip()

    images = []
    for img in page.eles("css:.article__content img"):
        cls = img.attr("class") or ""
        if "page-topper__mug" in cls:  # exclude the author headshot
            continue
        src = img.attr("src")
        if src:
            images.append(src)
    return content, "; ".join(images)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=int, default=1, help="listing pages to crawl")
    ap.add_argument("--max", type=int, default=0, help="max articles (0 = all found)")
    ap.add_argument("--out", default="mit_blogs_drissionpage.csv", help="output CSV path")
    ap.add_argument("--proxy", default=None,
                    help="HTTP(S) proxy for Disqus comment counts, e.g. http://127.0.0.1:7890 "
                         "(Disqus is unreachable in mainland China without one)")
    args = ap.parse_args()

    page, browser_used = make_browser(args.proxy)
    print(f"[browser] using {browser_used}")

    rows = []
    for page_no in range(1, args.pages + 1):
        list_url = BASE_URL if page_no == 1 else f"{BASE_URL}page/{page_no}/"
        print(f"[listing] {list_url}", flush=True)
        page.get(list_url, timeout=18)
        if not page.ele("css:article.tease", timeout=30):
            print("[warn] no article cards found")
            continue

        if not wait_for_comment_counts(page):
            print("[warn] Disqus counts not fully rendered; leaving blanks")

        cards = parse_listing(page)
        print(f"[listing] found {len(cards)} articles")
        for card in cards:
            m = re.search(r"\d+", card["commentText"])
            card["commentCount"] = m.group(0) if m else ""
        rows.extend(cards)

    if args.max > 0:
        rows = rows[: args.max]

    for i, row in enumerate(rows, 1):
        print(f"[article {i}/{len(rows)}] {row['url']}")
        try:
            row["content"], row["images"] = parse_article(page, row["url"])
        except Exception as e:
            print(f"[warn] failed: {e}")
            row["content"], row["images"] = "", ""
        time.sleep(0.5)  # be polite

    page.quit()

    out_fields = ["title", "author", "commentCount", "time", "content", "images"]
    headers = ["Title", "Author", "Comment Count", "Time", "Article Content", "Images In Article"]
    # utf-8-sig so Excel opens the file correctly
    with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row[k] for k in out_fields])

    print(f"[done] {len(rows)} rows -> {args.out}")


if __name__ == "__main__":
    main()
