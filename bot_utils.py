import logging
import os
import re
from typing import List

BOT_LIST_FILE = os.environ.get("BOT_LIST_FILE", "bot_user_agents.txt")


def load_bot_list(path: str = BOT_LIST_FILE) -> List[str]:
    """Load bot identifiers from a text file."""
    try:
        with open(path, "r", encoding="utf-8") as file:
            items = [
                line.strip()
                for line in file
                if line.strip() and not line.strip().startswith("#")
            ]
    except FileNotFoundError:
        logging.warning("Bot list file not found: %s", path)
        return []
    return sorted(set(items))


BOT_USER_AGENTS = load_bot_list()
BOT_PATTERN = re.compile("|".join(re.escape(ua) for ua in BOT_USER_AGENTS), re.I)


def is_bot(user_agent: str) -> bool:
    """Return True if the user agent matches a known bot."""
    return bool(BOT_PATTERN.search((user_agent or "").lower()))
