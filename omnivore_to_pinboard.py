import json
import os
from typing import Any

import omnivoreql
import pinboard

OMNIVORE_API = os.environ.get("OMNIVORE_API")
OMNIVORE_USERNAME = os.environ.get("OMNIVORE_USERNAME")
OMNIVORE_USER_ID = os.environ.get("OMNIVORE_USER_ID")
PINBOARD_API = os.environ.get("PINBOARD_API")


def omnivore_to_pinboard(event: dict, context: Any) -> None:
    body = json.loads(event["body"])
    if not body.get("userId") == OMNIVORE_USER_ID:
        print(
            f"userId {body.get('userId')} does not match {OMNIVORE_USER_ID}, skipping"
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
        print(f"Article fetching failed, errorcodes: {article.get('errorCodes')}")
        return
    article = article.get("article", {})
    print(f"Fetched article: {article['title']} {article['url']}")
    if not article.get("isArchived"):
        print("Fetched article is not archived, skipping")
        return
    labels = [label["name"] for label in article.get("labels", [])]
    print(f"Parsed labels: {labels}")
    description = article["description"] or ""
    highlights = []
    for highlight in article.get("highlights", []):
        h = f"\n\nQuote: {highlight['quote']}"
        if highlight["annotation"]:
            h += f"\nNote: {highlight['annotation']}"
        highlights.append(h)
    description += "".join(highlights)
    print(f"Description + highlights/notes: {description}")

    pb = pinboard.Pinboard(PINBOARD_API)
    pb.posts.add(
        url=article["url"],
        description=article["title"],
        extended=description,
        tags=labels,
    )
    print("Added to Pinboard")

    return
