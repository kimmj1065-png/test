import re
from typing import Dict, List

_DATE_PATTERN = re.compile(r"(\d{4})년\s+(\d{1,2})월\s+(\d{1,2})일")
_NEW_MSG_PATTERN = re.compile(r"^(오전|오후)\s+(\d{1,2}:\d{2}),\s+(.+?)\s+:\s+(.+)$")
_OLD_MSG_PATTERN = re.compile(r"^\[(.+?)\]\s+\[(오전|오후)\s+(\d{1,2}:\d{2})\]\s+(.+)$")


def parse_kakao_export(content: str) -> List[Dict[str, str]]:
    messages = []
    current_date = ""

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        date_match = _DATE_PATTERN.search(line)
        if date_match:
            year, month, day = date_match.groups()
            current_date = f"{year}-{int(month):02d}-{int(day):02d}"
            continue

        new_match = _NEW_MSG_PATTERN.match(line)
        if new_match:
            ampm, time, sender, text = new_match.groups()
            messages.append(
                {
                    "date": current_date,
                    "time": f"{ampm} {time}",
                    "sender": sender.strip(),
                    "text": text.strip(),
                }
            )
            continue

        old_match = _OLD_MSG_PATTERN.match(line)
        if old_match:
            sender, ampm, time, text = old_match.groups()
            messages.append(
                {
                    "date": current_date,
                    "time": f"{ampm} {time}",
                    "sender": sender.strip(),
                    "text": text.strip(),
                }
            )

    return messages


def extract_speakers(messages: List[Dict[str, str]]) -> List[str]:
    return list(dict.fromkeys(m["sender"] for m in messages))


def filter_by_sender(messages: List[Dict[str, str]], sender: str) -> List[Dict[str, str]]:
    return [m for m in messages if m["sender"] == sender]
