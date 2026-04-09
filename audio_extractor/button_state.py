from enum import Enum, auto

class ButtonState(Enum):
    IDLE = auto()
    FETCHED = auto()
    DOWNLOADING = auto() 