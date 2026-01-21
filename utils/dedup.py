from typing import List, Dict


def deduplicate_articles(
    articles: List[Dict],
    key: str = "url"
) -> List[Dict]:
    """
    Remove duplicate articles based on a unique key (default: url).
    Preserves order.
    """
    seen = set()
    unique = []

    for article in articles:
        value = article.get(key)
        if not value:
            continue

        if value not in seen:
            seen.add(value)
            unique.append(article)

    return unique
