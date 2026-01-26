from enum import Enum


class SourceType(str, Enum):
    TEXT = "text"
    FILE = "file"


class SummaryStatus(str, Enum):
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"

class SummaryLevel(str, Enum):
    AUTO = "auto"
    TLDR = "tldr"
    SHORT = "short"
    MEDIUM = "medium"
    DETAILED = "detailed"