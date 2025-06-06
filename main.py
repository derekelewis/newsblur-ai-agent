import logging
import os
from typing import Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI

from models import Feed, Story

# Setup
logging.basicConfig(level=logging.INFO)
load_dotenv()
openai = OpenAI()

# Parameters
MAX_STORIES = 5  # Number of stories to process
MAX_CONTENT_LENGTH = 3000  # Max length of story content to summarize
MAX_TOKENS = 2000
TEMPERATURE = 0.5
SYSTEM_PROMPT = """You are an assistant that summarizes news articles.
Please ensure that every article is summarized accurately. Insert the provided
permalink for each story into the placeholder below.
The summary should be in the following format:
1. *Feed title*
  1. *Story title* - story summary (1-3 sentences) <permalink|[Read more]>
  2. *Story title* - story summary (1-3 sentences) <permalink|[Read more]>
  ..
..
2. *Feed title*
etc.
"""


def authenticate_newsblur(username: str, password: str) -> Optional[requests.Session]:
    session = requests.Session()
    response = session.post(
        "https://newsblur.com/api/login",
        data={"username": username, "password": password},
    )
    if response.status_code != 200:
        logging.error(f"Authentication failed: {response.status_code}")
        return None
    return session


def fetch_feeds(session: requests.Session) -> Optional[list[Feed]]:
    response = session.get("https://newsblur.com/reader/feeds")
    if response.status_code != 200:
        logging.error(f"Failed to fetch feeds: {response.status_code}")
        return None
    feeds = [
        Feed(id=feed_id, title=feed_data["feed_title"])
        for feed_id, feed_data in response.json().get("feeds", {}).items()
    ]
    return feeds


def clean_html(html_content: str) -> str:
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()


def fetch_feed_stories(session: requests.Session, feed: Feed) -> Optional[list[Story]]:
    stories = []
    response = session.get(
        f"https://newsblur.com/reader/feed/{feed.id}",
        params={"read_filter": "unread"},
    )
    if response.status_code != 200:
        logging.error(
            f"Failed to fetch stories for feed id {feed.id}: {response.status_code}"
        )
        return None

    raw_stories = response.json().get("stories", [])

    if not raw_stories:
        logging.info(f"No stories found for {feed.id} - {feed.title}")
        return []
    else:
        logging.info(
            f"{len(raw_stories)} stories found for {feed.id} - {feed.title}")

    for raw_story in raw_stories[:MAX_STORIES]:
        story_title = raw_story.get("story_title")
        story_content_html = raw_story.get("story_content")
        story_permalink = raw_story.get("story_permalink")
        story_hash = raw_story.get("story_hash")

        # Clean the HTML content
        story_content_text = clean_html(story_content_html)

        # Fetch content directly if RSS is empty or short
        if len(story_content_text) < 100:
            logging.info(
                f"Story content for f{story_hash} may be empty from RSS feed. Fetching directly..."
            )
            story_content_text = fetch_webpage(story_permalink)

        # Truncate content if necessary
        if len(story_content_text) > MAX_CONTENT_LENGTH:
            story_content_text = story_content_text[:MAX_CONTENT_LENGTH]

        stories.append(
            Story(story_hash, story_title, story_content_text, story_permalink)
        )
    return stories


# TODO: implement chunking for stories because NB API only
# supports up to 5 story_hashes, but fine if MAX_STORIES = 5
def mark_stories_as_read(session: requests.Session, feeds: list[Feed]) -> None:
    if not feeds:
        return None
    story_hashes = [[story.hash for story in feed.stories] for feed in feeds]
    for stories in story_hashes:
        response = session.post(
            "https://newsblur.com/reader/mark_story_hashes_as_read",
            data=[("story_hash", story_hash) for story_hash in stories],
        )
        logging.info(f"Marked {len(stories)} stories as read")
        if response.status_code != 200:
            logging.error(
                f"Failed to mark stories as read: {response.status_code}")


def summarize_stories(feeds: list[Feed], model_id: str) -> str | None:
    content = "Please summarize the following articles.\n\n"
    for feed in feeds:
        content += f"Feed: {feed.title}\n"
        for story in feed.stories:
            content += f"Title: {story.title}\n"
            content += f"Content: {story.content_text}\n"
            content += f"Link: {story.permalink}\n\n"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": content,
        },
    ]
    response = openai.chat.completions.create(
        model=model_id,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )
    return response.choices[0].message.content


def send_to_slack(summary: str, webhook_url: str) -> None:
    slack_data = {
        "text": f"Here is the latest summarized news:\n\n{summary}",
        "unfurl_links": False,
        "unfurl_media": False,
    }
    response = requests.post(
        webhook_url, json=slack_data, headers={
            "Content-Type": "application/json"}
    )
    if response.status_code != 200:
        logging.error(
            f"Failed to send message to Slack: {response.status_code}")


def fetch_webpage(url):
    response = requests.get(url)
    if response.status_code != 200:
        logging.error(
            f"Failed to fetch content for {url}: {response.status_code}")
        return None
    page_text = clean_html(response.content)
    return page_text


def main():
    NEWSBLUR_USERNAME = os.getenv("NEWSBLUR_USERNAME")
    NEWSBLUR_PASSWORD = os.getenv("NEWSBLUR_PASSWORD")
    MODEL_ID = os.getenv("MODEL_ID")
    WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
    MARK_STORIES_AS_READ = os.getenv(
        "MARK_STORIES_AS_READ", "false").lower() == "true"

    session = authenticate_newsblur(NEWSBLUR_USERNAME, NEWSBLUR_PASSWORD)
    if not session:
        logging.info("No session")
        return

    feeds = fetch_feeds(session)
    if not feeds:
        logging.info("No feeds")
        return

    for feed in feeds:
        feed.stories = fetch_feed_stories(session, feed)

    feeds_with_stories = [feed for feed in feeds if feed.stories]
    if not feeds_with_stories:
        logging.info("No feed stories")
        return

    try:
        summary = summarize_stories(feeds_with_stories, MODEL_ID)
    except Exception as e:
        logging.error(f"Failed to summarize stories: {e}")
        return

    logging.info(f"Summary:\n\n{summary}")

    send_to_slack(summary, WEBHOOK_URL)

    if MARK_STORIES_AS_READ:
        mark_stories_as_read(session, feeds_with_stories)


if __name__ == "__main__":
    main()
