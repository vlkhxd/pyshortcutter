import ctypes

user32 = ctypes.windll.user32

# Media keys (Windows VK codes)
VK_MEDIA_PLAY_PAUSE = 0xB3
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1  # <-- NEW
VK_VOLUME_MUTE      = 0xAD
VK_VOLUME_DOWN      = 0xAE
VK_VOLUME_UP        = 0xAF

KEYEVENTF_KEYUP = 0x0002


def press_vk(vk: int) -> None:
    """Send a media key event to Windows."""
    user32.keybd_event(vk, 0, 0, 0)
    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)