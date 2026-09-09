import os
import json
import hashlib
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "397982523")

URL = "https://mppsc.mp.gov.in/"
STATE_FILE = "mppsc_state.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
    )
}


def get_page():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=40
    )
    response.raise_for_status()
    return response.text


def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = " ".join(
        soup.get_text(" ", strip=True).split()
    )

    links = []
    seen = set()

    for a in soup.find_all("a", href=True):
        title = " ".join(
            a.get_text(" ", strip=True).split()
        )

        href = a.get("href", "").strip()

        if not href:
            continue

        full_url = urljoin(URL, href)

        key = (title, full_url)

        if key not in seen:
            seen.add(key)
            links.append({
                "title": title,
                "url": full_url
            })

    return text, links


def make_hash(text):
    return hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(
            STATE_FILE,
            "r",
            encoding="utf-8"
        ) as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(
        STATE_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            state,
            f,
            ensure_ascii=False,
            indent=2
        )


def send_telegram(message):
    if not BOT_TOKEN:
        print("BOT_TOKEN is missing.")
        return False

    telegram_url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        telegram_url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False
        },
        timeout=30
    )

    if response.status_code != 200:
        print("Telegram Error:", response.text)
        return False

    return True


def monitor():

    print("=" * 60)
    print("MPPSC WEBSITE MONITOR")
    print(datetime.now().strftime(
        "%d-%m-%Y %I:%M:%S %p"
    ))
    print("=" * 60)

    old_state = load_state()

    try:
        html = get_page()

        text, links = parse_page(html)

        current_hash = make_hash(text)

        new_state = {
            "hash": current_hash,
            "text": text,
            "links": links,
            "checked": datetime.now().isoformat()
        }

        if not old_state:
            save_state(new_state)
            print("Initial MPPSC snapshot created.")
            return

        old_hash = old_state.get("hash")

        if old_hash == current_hash:
            save_state(new_state)
            print("No MPPSC change.")
            return

        old_links = {
            (x["title"], x["url"])
            for x in old_state.get("links", [])
        }

        new_links = {
            (x["title"], x["url"])
            for x in links
        }

        added = new_links - old_links

        important = []

        for title, link in added:

            value = (
                f"{title} {link}"
            ).lower()

            keywords = [
                "notification",
                "advertisement",
                "recruitment",
                "exam",
                "examination",
                "application",
                "online",
                "result",
                "answer key",
                "admit card",
                "interview",
                "selection",
                "vacancy",
                "syllabus",
                "calendar",
                "time table",
                "schedule",
                "notice",
                "pdf",
                ".pdf"
            ]

            if any(
                keyword in value
                for keyword in keywords
            ):
                important.append(
                    (title, link)
                )

        save_state(new_state)

        if not important:
            print(
                "MPPSC changed, but no important "
                "new link found."
            )
            return

        message = (
            "🏛️ MPPSC IMPORTANT UPDATE\n\n"
        )

        message += (
            "⏰ "
            + datetime.now().strftime(
                "%d-%m-%Y %I:%M %p"
            )
            + "\n\n"
        )

        message += "🆕 NEW UPDATE:\n\n"

        for title, link in important[:10]:

            if not title:
                title = "MPPSC New Update"

            message += (
                f"📢 {title}\n"
                f"🔗 {link}\n\n"
            )

        message += (
            "🌐 MPPSC Official Website:\n"
            "https://mppsc.mp.gov.in/\n\n"
            "🤖 MPPSC Automatic Monitor"
        )

        if len(message) > 3900:
            message = message[:3900] + "\n..."

        if send_telegram(message):
            print(
                "Telegram notification sent successfully."
            )
        else:
            print(
                "Telegram notification failed."
            )

    except Exception as e:

        print(
            "ERROR while checking MPPSC:",
            e
        )


if __name__ == "__main__":
    monitor()
