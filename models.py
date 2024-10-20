from dataclasses import dataclass, field

@dataclass
class Story:
    hash: str
    title: str
    content_text: str
    permalink: str

@dataclass
class Feed:
    id: str
    title: str
    stories: list[Story] = field(default_factory=list)