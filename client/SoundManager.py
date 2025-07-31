# voice.py
from pathlib import Path
from threading import Thread
from playsound import playsound
from enums.EventType import EventType
from message_bus import subscribe

SOUNDS_DIR = Path("./sounds")

def _play_async(path: Path):
    """
    Play an audio file asynchronously in a separate thread.
    
    Args:
        path (Path): Path to the audio file
        
    Returns:
        bool: True if playback started successfully, False otherwise
    """
    try:
        # First verify the file exists before trying to play it
        if path.exists():
            Thread(target=playsound, args=(str(path),), daemon=True).start()
            return True
        else:
            print(f"Warning: Sound file not found: {path}")
            return False
    except Exception as e:
        print(f"Error playing sound: {e}")
        return False

class VoiceSFX:
    """
    Listens for game events and plays appropriate sound effects.
    """
    def __init__(self):
        subscribe(EventType.PIECE_MOVED, self._on_move)
        subscribe(EventType.PIECE_CAPTURED, self._on_capture)
        subscribe(EventType.INVALID_MOVE, self._on_invalid_move)
        subscribe(EventType.GAME_START, self._begin_game)
        subscribe(EventType.GAME_END, self._on_game_over)

    def _on_move(self, data):
        _play_async(SOUNDS_DIR / "move.wav")

    def _on_capture(self, data):
        _play_async(SOUNDS_DIR / "capture.mp3")

    def _on_invalid_move(self, data):
        _play_async(SOUNDS_DIR / "invalid.mp3")

    def _begin_game(self, data):
        _play_async(SOUNDS_DIR / "start_game.mp3")

    def _on_game_over(self, data):
        _play_async(SOUNDS_DIR / "game_over.wav")