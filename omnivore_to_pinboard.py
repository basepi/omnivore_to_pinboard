import json
import os
from typing import Any

import boto3
import omnivoreql
import pinboard

OMNIVORE_API = os.environ.get("OMNIVORE_API")
OMNIVORE_USERNAME = os.environ.get("OMNIVORE_USERNAME")
OMNIVORE_USER_ID = os.environ.get("OMNIVORE_USER_ID")
PINBOARD_API = os.environ.get("PINBOARD_API")
NOTIFICATION_EMAIL = os.environ.get("NOTIFICATION_EMAIL")

ses = boto3.client("ses")


def omnivore_to_pinboard(event: dict, context: Any) -> None:
    body = json.loads(event["body"])
    if not body.get("userId") == OMNIVORE_USER_ID:
        send_email_notification(
            f"userId {body.get('userId')} does not match {OMNIVORE_USER_ID}, skipping",
            {},
        )
        return  # The tiniest bit of insurance against bad actors?
    if not body.get("page", {}).get("archivedAt"):
        print("Not archived, skipping")
        return  # Only care when it's archived
    article_id = body["page"]["id"]

    # Fetch article details
    omnivore = omnivoreql.OmnivoreQL(OMNIVORE_API)
    article = omnivore.get_article(OMNIVORE_USERNAME, article_id).get("article", {})
    if not article.get("article"):
        send_email_notification(
            f"Article fetching failed, errorcodes: {article.get('errorCodes')}", article
        )
        return
    article = article.get("article", {})
    print(f"Fetched article: {article['title']} {article.get('url')}")
    if not article.get("isArchived"):
        print("Fetched article is not archived, skipping")
        return
    labels = [label["name"] for label in article.get("labels", [])]
    print(f"Parsed labels: {labels}")
    if "000noarchive" in labels:
        print("Fetched article has noarchive label, skipping")
        return
    if not article.get("url"):
        send_email_notification(
            "Fetched article has no URL + missing noarchive label, skipping", article
        )
        return
    description = article["description"] or ""
    highlights = []
    for highlight in article.get("highlights", []):
        h = f"\n\nQuote: {highlight['quote']}"
        if highlight["annotation"]:
            h += f"\nNote: {highlight['annotation']}"
        highlights.append(h)
    description += "".join(highlights)
    print(f"Description + highlights/notes: {description}")

    try:
        pb = pinboard.Pinboard(PINBOARD_API)
        pb.posts.add(
            url=article["url"],
            description=article["title"],
            extended=description,
            tags=labels,
        )
    except Exception as e:
        send_email_notification(f"Pinboard error: {e}", article)
        return
    print("Added to Pinboard")

    return


def send_email_notification(error: str, article: dict) -> None:
    print(error)
    if not NOTIFICATION_EMAIL:
        return
    ses.send_email(
        Destination={
            "ToAddresses": [
                NOTIFICATION_EMAIL,
            ],
        },
        Message={
            "Body": {
                "Text": {
                    "Charset": "UTF-8",
                    "Data": f"Error: {error}\n\nArticle: {article}",
                },
            },
            "Subject": {
                "Charset": "UTF-8",
                "Data": "Error saving to Omnivore",
            },
        },
        Source=NOTIFICATION_EMAIL,
    )
