from enum import Enum, auto

class RoomLight(Enum):
    """Room lighting states"""
    DARK = auto()
    PHONE_GLOW = auto()  # device_lit
    LIT = auto()         # room_lit

class Tutorial(Enum):
    """Tutorial progression states"""
    NOT_STARTED = auto()
    DEVICE_PICKED = auto()
    NAME_SET = auto()
    PATCH_INTRO_DONE = auto()
    MIRROR_PROMPTED = auto()
    MIRROR_PHOTO_TAKEN = auto()
    ARTICLE_PROMPTED = auto()
    ARTICLE_PHOTOS_DONE = auto()
    COMPLETE = auto()

def advance_tutorial(current: Tutorial, event: str) -> Tutorial:
    """Advance tutorial state based on events"""
    transitions = {
        (Tutorial.NOT_STARTED, "device_picked"): Tutorial.DEVICE_PICKED,
        (Tutorial.DEVICE_PICKED, "name_set"): Tutorial.NAME_SET,
        (Tutorial.NAME_SET, "patch_intro_done"): Tutorial.PATCH_INTRO_DONE,
        (Tutorial.PATCH_INTRO_DONE, "mirror_prompted"): Tutorial.MIRROR_PROMPTED,
        (Tutorial.MIRROR_PROMPTED, "mirror_photo_taken"): Tutorial.MIRROR_PHOTO_TAKEN,
        (Tutorial.MIRROR_PHOTO_TAKEN, "article_prompted"): Tutorial.ARTICLE_PROMPTED,
        (Tutorial.ARTICLE_PROMPTED, "article_photos_done"): Tutorial.ARTICLE_PHOTOS_DONE,
        (Tutorial.ARTICLE_PHOTOS_DONE, "complete"): Tutorial.COMPLETE,
    }
    
    return transitions.get((current, event), current)

def room_light_to_string(light: RoomLight) -> str:
    """Convert enum to string for backward compatibility"""
    mapping = {
        RoomLight.DARK: 'dark',
        RoomLight.PHONE_GLOW: 'device_lit', 
        RoomLight.LIT: 'room_lit'
    }
    return mapping[light]

def string_to_room_light(light_str: str) -> RoomLight:
    """Convert string to enum for backward compatibility"""
    mapping = {
        'dark': RoomLight.DARK,
        'device_lit': RoomLight.PHONE_GLOW,
        'room_lit': RoomLight.LIT
    }
    return mapping.get(light_str, RoomLight.DARK)



