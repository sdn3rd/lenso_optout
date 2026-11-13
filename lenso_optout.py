#!/usr/bin/env python3
"""
Fills the lenso.ai image opt-out form for every image in ~/Desktop/PFace/,
one image at a time in numerical order, then waits for you to click Submit
in the browser before loading the next image.

This connects to your normal, already-running Chrome over its remote
debugging port instead of launching a separate browser instance. Before
running the script, fully quit Chrome (Cmd+Q) and relaunch it with:

    open -a "Google Chrome" --args --remote-debugging-port=9222

Setup:
    python3 -m venv .venv && source .venv/bin/activate
    pip install playwright

    (No "playwright install chromium" needed here since we're attaching
    to your existing Chrome rather than launching Playwright's own copy.)

Run:
    python lenso_optout.py
"""

import argparse
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# EDIT THESE
# ---------------------------------------------------------------------------

FIRST_NAME = "Jane"
LAST_NAME = "Doe"
EMAIL = "jane.doe9@gmail.com"

# Must be at least 20 characters. Explain in your own words why you want
# these images removed.
DESCRIPTION = (
    "I do not consent to these images of me being indexed or shown in "
    "search results. Please remove them."
)

IMAGE_DIR = Path.home() / "Desktop" / "PFace"

# ---------------------------------------------------------------------------

URL = "https://lenso.ai/en/opt-out"
EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DONE_LOG = Path(__file__).with_name("lenso_submitted.txt")
CDP_URL = "http://localhost:9222"


def natural_key(p: Path):
    """Sort 2.jpg before 10.jpg."""
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", p.name)]


def load_done() -> set:
    if DONE_LOG.exists():
        return {line for line in DONE_LOG.read_text().split("\n") if line}
    return set()


def mark_done(name: str):
    with DONE_LOG.open("a") as f:
        f.write(name + "\n")


def dismiss_banner(page):
    for label in ("Reject all", "Only necessary", "Decline", "Accept"):
        btn = page.get_by_role("button", name=label, exact=False)
        try:
            if btn.count():
                btn.first.click(timeout=2000)
                return
        except Exception:
            pass


def fill_form(page, image: Path):
    page.goto(URL, wait_until="domcontentloaded")
    dismiss_banner(page)

    page.set_input_files("#opt-out-file-upload", str(image))
    page.fill("#opt-out-description", DESCRIPTION)
    page.fill("#opt-out-first-name", FIRST_NAME)
    page.fill("#opt-out-last-name", LAST_NAME)
    page.fill("#opt-out-email", EMAIL)

    # Four consent checkboxes. The inputs are display:none and their labels
    # contain Privacy Policy and Terms links, so clicking a label navigates
    # away. Click the input element itself instead, which toggles it without
    # hitting the links.
    for i in range(1, 5):
        box_id = f"checkbox-input-{i}"
        box = page.locator(f"#{box_id}")
        if box.is_checked():
            continue
        page.evaluate(
            "id => { const el = document.getElementById(id);"
            " if (el && !el.checked) el.click(); }",
            box_id,
        )
        if not box.is_checked():
            raise RuntimeError(f"could not tick {box_id}")

    page.locator("button.opt-out-form__submit").scroll_into_view_if_needed()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(IMAGE_DIR))
    ap.add_argument("--redo", action="store_true", help="ignore the submitted log")
    args = ap.parse_args()

    image_dir = Path(args.dir).expanduser()
    if not image_dir.is_dir():
        sys.exit(f"No such directory: {image_dir}")

    images = sorted(
        (p for p in image_dir.iterdir() if p.suffix.lower() in EXTS and p.is_file()),
        key=natural_key,
    )
    if not images:
        sys.exit(f"No images found in {image_dir}")

    done = set() if args.redo else load_done()
    queue = [p for p in images if p.name not in done]
    print(f"{len(images)} images found, {len(queue)} left to do")

    skipped = []
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.connect_over_cdp(CDP_URL)
        except Exception as e:
            sys.exit(
                f"Could not connect to Chrome at {CDP_URL}: {e}\n"
                "Make sure Chrome was fully quit and relaunched with:\n"
                '  open -a "Google Chrome" --args --remote-debugging-port=9222'
            )

        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        for n, image in enumerate(queue, 1):
            print(f"\n[{n}/{len(queue)}] {image.name}")
            try:
                fill_form(page, image)
            except Exception as e:
                print(f"  error filling: {e}")
                skipped.append(image.name)
                continue

            print("  filled. Click Submit in the browser, then come back here:")
            print("    Enter = submitted, reload the form with the next image")
            print("    s     = skip this one, do not log it")
            print("    q     = quit")
            try:
                answer = input("  > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print("\n  stopping")
                break

            if answer == "q":
                print("  quitting")
                break
            if answer == "s":
                skipped.append(image.name)
                print("  skipped")
                continue

            mark_done(image.name)
            print("  logged as submitted")

        page.close()
        # Note: we deliberately don't call browser.close() here - that
        # would disconnect from (and may quit) your actual running Chrome,
        # which this script is just borrowing a tab from.

    print("\nStopped.")
    if skipped:
        print("Not logged: " + ", ".join(skipped))
    print(f"Log: {DONE_LOG}")


if __name__ == "__main__":
    main()
