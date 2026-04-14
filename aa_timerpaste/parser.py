import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


REINFORCED_RE = re.compile(r"Reinforced until\s+(\d{4}\.\d{2}\.\d{2}\s+\d{2}:\d{2}:\d{2})", re.I)
DISCORD_TIMESTAMP_RE = re.compile(r"—\s*(?:\d{1,2}/\d{1,2}/\d{4}|Yesterday at)\s+[\d:]+", re.I)
MENTION_RE = re.compile(r"^@\S+")
DISTANCE_RE = re.compile(r"^\s*[\d.,\s]+(?:m|km|AU)\s*$", re.I)
SECURITY_RE = re.compile(r"^\s*Sec\.\s*[\d.,]+\s*$", re.I)
SKYHOOK_RE = re.compile(r"Orbital Skyhook\s+\((?P<inside>[^)]+)\)\s+\[(?P<owner>[^\]]+)\]", re.I)
SYSTEM_MOON_RE = re.compile(r"^(?P<system>[A-Z0-9-]+)\s*-\s*(?P<location>.+)$")
BRIDGE_RE = re.compile(r"^(?P<source>[A-Z0-9-]+)\s*»\s*(?P<dest>[A-Z0-9-]+)\s*-\s*(?P<label>.+)$")
STRUCTURE_KEYWORDS = {
    "orbital skyhook": "skyhook",
    "metenox": "metenox",
    "mercenary den": "mercenary_den",
    "ansiblex": "ansiblex",
    "ansi": "ansiblex",
    "astrahus": "astrahus",
    "astra": "astrahus",
    "athanor": "athanor",
    "fortizar": "fortizar",
    "pos": "pos",
    "poco": "poco",
}


@dataclass
class ParsedTimer:
    raw_text: str
    details: str = ""
    objective: str = "unknown"
    system_name: str = ""
    moon_or_location: str = ""
    structure_type: str = "other"
    owner_name: str = ""
    distance_text: str = ""
    timer_at: Optional[datetime] = None
    parse_status: str = "parsed"
    parse_notes: list[str] = field(default_factory=list)

    def as_dict(self):
        return {
            "raw_text": self.raw_text,
            "details": self.details,
            "objective": self.objective,
            "system_name": self.system_name,
            "moon_or_location": self.moon_or_location,
            "structure_type": self.structure_type,
            "owner_name": self.owner_name,
            "distance_text": self.distance_text,
            "timer_at": self.timer_at,
            "parse_status": self.parse_status,
            "parse_notes": "; ".join(self.parse_notes),
        }


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def is_noise(line: str) -> bool:
    s = normalize_line(line)
    if not s:
        return True
    if MENTION_RE.match(s):
        return True
    if DISCORD_TIMESTAMP_RE.search(s):
        return True
    if s.lower() in {"done", "all added", "machine", "k"}:
        return True
    return False


def infer_structure_type(lines: list[str]) -> str:
    joined = " | ".join(lines).lower()
    for key, value in STRUCTURE_KEYWORDS.items():
        if key in joined:
            return value
    if any("»" in x for x in lines):
        return "ansiblex"
    return "other"


def infer_objective(lines: list[str]) -> str:
    joined = " ".join(lines).lower()
    if any(k in joined for k in ["hostile", "noco", "northern coalition", "fraternity", "frat", "dice"]):
        return "hostile"
    if "friendly" in joined:
        return "friendly"
    return "unknown"


def parse_timer_block(block: str) -> Optional[ParsedTimer]:
    raw_lines = [normalize_line(x) for x in block.splitlines()]
    lines = [x for x in raw_lines if x and not is_noise(x)]
    if not lines:
        return None

    timer_match = None
    for line in lines:
        timer_match = REINFORCED_RE.search(line)
        if timer_match:
            break
    if not timer_match:
        return None

    timer_at = datetime.strptime(timer_match.group(1), "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
    data = ParsedTimer(raw_text=block.strip(), timer_at=timer_at)
    data.structure_type = infer_structure_type(lines)
    data.objective = infer_objective(lines)

    for line in lines:
        if REINFORCED_RE.search(line):
            continue
        if DISTANCE_RE.match(line):
            data.distance_text = line
            continue
        if SECURITY_RE.match(line):
            if data.distance_text:
                data.distance_text += f" | {line}"
            else:
                data.distance_text = line
            continue

        sky = SKYHOOK_RE.search(line)
        if sky:
            inside = sky.group("inside").strip()
            owner = sky.group("owner").strip()
            data.owner_name = owner
            data.structure_type = "skyhook"
            tokens = inside.split()
            if tokens:
                data.system_name = tokens[0]
                data.moon_or_location = inside[len(tokens[0]):].strip()
            continue

        bridge = BRIDGE_RE.match(line)
        if bridge:
            data.system_name = bridge.group("source").strip()
            data.moon_or_location = f"{bridge.group('dest').strip()} - {bridge.group('label').strip()}"
            data.structure_type = "ansiblex"
            continue

        sysmoon = SYSTEM_MOON_RE.match(line)
        if sysmoon:
            candidate_system = sysmoon.group("system").strip()
            candidate_loc = sysmoon.group("location").strip()
            if candidate_system and not data.system_name:
                data.system_name = candidate_system
                data.moon_or_location = candidate_loc
                continue

        if line.lower() in {"mercenary den", "orbital skyhook", "metenox", "astra", "athanor", "fortizar", "pos", "poco"}:
            if data.structure_type == "other":
                data.structure_type = STRUCTURE_KEYWORDS.get(line.lower(), "other")
            continue

        if not data.details:
            data.details = line

    if not data.system_name:
        data.parse_status = "unknown_system"
        data.parse_notes.append("No system could be extracted from pasted text.")

    if not data.details:
        data.details = data.raw_text.splitlines()[0][:255]

    return data


def split_blocks(raw_text: str) -> list[str]:
    lines = raw_text.replace("\r\n", "\n").split("\n")
    blocks = []
    current = []

    for line in lines:
        current.append(line)
        if REINFORCED_RE.search(line):
            blocks.append("\n".join(current).strip())
            current = []

    if current:
        remainder = "\n".join(current).strip()
        if remainder:
            blocks.append(remainder)

    return [b for b in blocks if REINFORCED_RE.search(b)]


def parse_many(raw_text: str) -> list[ParsedTimer]:
    results = []
    for block in split_blocks(raw_text):
        parsed = parse_timer_block(block)
        if parsed:
            results.append(parsed)
    return results
