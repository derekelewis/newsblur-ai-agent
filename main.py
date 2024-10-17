import requests
import logging
from openai import OpenAI
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os
import datetime

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


def authenticate_newsblur(username, password):
    response = requests.post(
        "https://newsblur.com/api/login",
        data={"username": username, "password": password},
    )
    if response.status_code != 200:
        logging.error(f"Authentication failed: {response.status_code}")
    return response.cookies


def fetch_feeds(cookies):
    response = requests.get("https://newsblur.com/reader/feeds", cookies=cookies)
    if response.status_code != 200:
        logging.error(f"Failed to fetch feeds: {response.status_code}")
        return None
    return response.json().get("feeds", {})


def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    return soup.get_text()[:MAX_CONTENT_LENGTH]


def fetch_feed_stories(cookies, feeds):
    feed_dict = {}
    for feed_id, feed in feeds.items():
        stories = []
        response = requests.get(
            f"https://newsblur.com/reader/feed/{feed_id}",
            cookies=cookies,
            params={"read_filter": "unread"},
        )
        if response.status_code != 200:
            logging.error(
                f"Failed to fetch stories for feed id {feed_id}: {response.status_code}"
            )
            return None

        raw_stories = response.json().get("stories", [])

        if not raw_stories:
            logging.info(f"No stories found for {feed['id']} - {feed['feed_title']}")
            continue
        else:
            logging.info(
                f"{len(raw_stories)} stories found for {feed['id']} - {feed['feed_title']}"
            )

        for raw_story in raw_stories[:MAX_STORIES]:
            story_title = raw_story.get("story_title")
            story_content_html = raw_story.get("story_content")
            story_permalink = raw_story.get("story_permalink")
            story_hash = raw_story.get("story_hash")

            # Clean the HTML content
            story_content_text = clean_html(story_content_html)

            # Truncate content if necessary
            if len(story_content_text) > MAX_CONTENT_LENGTH:
                story_content_text = story_content_text[:MAX_CONTENT_LENGTH]

            stories.append(
                {
                    "story_hash": story_hash,
                    "story_title": story_title,
                    "story_content_text": story_content_text,
                    "story_permalink": story_permalink,
                }
            )

        feed_dict[feed["feed_title"]] = stories
    return feed_dict


# TODO: implement chunking for stories because NB API only
# supports up to 5 story_hashes, but fine if MAX_STORIES = 5
def mark_stories_as_read(cookies, feed_dict):
    if not feed_dict:
        return
    story_hashes = [
        [story["story_hash"] for story in feed] for feed in feed_dict.values()
    ]
    for stories in story_hashes:
        response = requests.post(
            "https://newsblur.com/reader/mark_story_hashes_as_read",
            cookies=cookies,
            data=[("story_hash", story_hash) for story_hash in stories],
        )
        logging.info(f"Marked {len(stories)} stories as read")
        if response.status_code != 200:
            logging.error(f"Failed to mark stories as read")


def summarize_stories(feed_dict, model_id):
    content = "Please summarize the following articles.\n\n"
    for feed_title, stories in feed_dict.items():
        content += f"Feed: {feed_title}\n"
        for story in stories:
            content += f"Title: {story['story_title']}\n"
            content += f"Content: {story['story_content_text']}\n"
            content += f"Link: {story['story_permalink']}\n\n"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": content,
        },
    ]
    try:
        response = openai.chat.completions.create(
            model=model_id,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"OpenAI API error: {e}")
        return ""


def send_to_slack(summary, webhook_url):
    date = datetime.datetime.now().strftime("%m/%d/%y %I:%M %p")
    slack_data = {
        "text": f"Here is the latest summarized news:\n\n{summary}",
        "unfurl_links": False,
        "unfurl_media": False,
    }
    response = requests.post(
        webhook_url, json=slack_data, headers={"Content-Type": "application/json"}
    )
    if response.status_code != 200:
        logging.error(f"Failed to send message to Slack: {response.status_code}")


def main():
    NEWSBLUR_USERNAME = os.getenv("NEWSBLUR_USERNAME")
    NEWSBLUR_PASSWORD = os.getenv("NEWSBLUR_PASSWORD")
    MODEL_ID = os.getenv("MODEL_ID")
    WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
    MARK_STORIES_AS_READ = os.getenv("MARK_STORIES_AS_READ", "false").lower() == "true"

    cookies = authenticate_newsblur(NEWSBLUR_USERNAME, NEWSBLUR_PASSWORD)
    if not cookies:
        logging.info("No cookies")
        return

    feeds = fetch_feeds(cookies)
    if not feeds:
        logging.info("No feeds")
        return

    feed_stories = fetch_feed_stories(cookies, feeds)
    if not feed_stories:
        logging.info("No feed stories")
        return

    summary = summarize_stories(feed_stories, MODEL_ID)
    logging.info(f"Summary:\n\n{summary}")

    send_to_slack(summary, WEBHOOK_URL)

    if MARK_STORIES_AS_READ:
        mark_stories_as_read(cookies, feed_stories)


if __name__ == "__main__":
    main()
