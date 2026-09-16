"""Crawl https://mitadmissions.org/blogs/ with Playwright and save a CSV.

Columns: Title | Author | Comment Count | Time | Article Content | Images In Article

Key detail: the comment count on the listing page is rendered client-side by
Disqus count.js (the anchor is empty in the raw HTML), so a real browser is
required. Comment counts are read from the listing page; article bodies and
images come from each article page.

Usage:
    python crawl_playwright.py --pages 1 --max 0 --out mit_blogs_playwright.csv
"""

import argparse
import csv
import re
import time

from playwright.sync_api import sync_playwright

BASE_URL = "https://mitadmissions.org/blogs/"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
DISQUS_LINK_SEL = "a[href$='#disqus_thread']"


def launch_browser(pw, proxy=None):
    """Prefer the bundled Chromium; fall back to locally installed browsers."""
    attempts = [
        dict(headless=True),
        dict(headless=True, channel="chrome"),
        dict(headless=True, channel="msedge"),
    ]
    if proxy:
        for kwargs in attempts:
            kwargs["proxy"] = {"server": proxy}
    last_error = None
    for kwargs in attempts:
        try:
            return pw.chromium.launch(**kwargs), kwargs.get("channel", "chromium")
        except Exception as e:  # browser executable not installed, etc.
            last_error = e
    raise RuntimeError(f"Could not launch any Chromium-based browser: {last_error}")


def wait_for_comment_counts(page, timeout_s=20):
    """Poll until Disqus count.js has filled every comment-count anchor."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        texts = page.eval_on_selector_all(
            DISQUS_LINK_SEL, "els => els.map(e => e.textContent.trim())"
        )
        if texts and all(texts):
            return True
        page.wait_for_timeout(500)
    return False


def parse_listing(page):
    """Extract one row per article card on the listing page."""
    return page.eval_on_selector_all(
        "article.tease",
        """cards => cards.map(card => {
            const link = card.querySelector('a.post-tease__h__link');
            if (!link) return null;
            const title = card.querySelector('.post-tease__title');
            const author = card.querySelector('.post-tease__meta-item--author a');
            const date = card.querySelector('.tease__meta-item--date');
            const count = card.querySelector("a[href$='#disqus_thread']");
            return {
                title: title ? title.textContent.trim() : link.textContent.trim(),
                author: author ? author.textContent.trim() : '',
                time: date ? date.textContent.trim() : '',
                commentText: count ? count.textContent.trim() : '',
                url: link.href,
            };
        }).filter(Boolean)""",
    )


def parse_article(page, url):
    """Fetch one article page and return (content_text, images_joined)."""
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_selector(".article__body", timeout=30000)

    content = page.eval_on_selector(
        ".article__body", "e => e.innerText.trim()"
    )
    images = page.eval_on_selector_all(
        # exclude the author headshot shown above the body
        ".article__content img:not(.page-topper__mug)",
        "els => els.map(e => e.src)",
    )
    return content, "; ".join(images)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pages", type=int, default=1, help="listing pages to crawl")
    ap.add_argument("--max", type=int, default=0, help="max articles (0 = all found)")
    ap.add_argument("--out", default="mit_blogs_playwright.csv", help="output CSV path")
    ap.add_argument("--proxy", default=None,
                    help="HTTP(S) proxy for Disqus comment counts, e.g. http://127.0.0.1:7890 "
                         "(Disqus is unreachable in mainland China without one)")
    args = ap.parse_args()

    rows = []
    with sync_playwright() as pw:
        browser, channel = launch_browser(pw, args.proxy)
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1366, "height": 900})
        page = context.new_page()

        for page_no in range(1, args.pages + 1):
            list_url = BASE_URL if page_no == 1 else f"{BASE_URL}page/{page_no}/"
            print(f"[listing] {list_url}")
            page.goto(list_url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_selector("article.tease", timeout=30000)

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

        browser.close()

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
