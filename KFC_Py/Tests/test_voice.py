import unittest
from unittest.mock import patch, call
import sys
import os
from pathlib import Path
from threading import Thread
from playsound import playsound

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from KFC_Py.SoundManager import _play_async, VoiceSFX, SOUNDS_DIR

class TestVoiceSFX(unittest.TestCase):
    @patch('voice._play_async')
    def test_on_move(self, mock_play_async):
        """Test that _on_move calls _play_async with the correct sound file."""
        vsfx = VoiceSFX()
        vsfx._on_move({"dummy": "data"})
        mock_play_async.assert_called_with(SOUNDS_DIR / "move.wav")
    
    @patch('voice._play_async')
    def test_on_capture(self, mock_play_async):
        """Test that _on_capture calls _play_async with the correct sound file."""
        vsfx = VoiceSFX()
        vsfx._on_capture({"dummy": "data"})
        mock_play_async.assert_called_with(SOUNDS_DIR / "capture.mp3")
    
    @patch('voice._play_async')
    def test_on_invalid_move(self, mock_play_async):
        """Test that _on_invalid_move calls _play_async with the correct sound file."""
        vsfx = VoiceSFX()
        vsfx._on_invalid_move({"dummy": "data"})
        mock_play_async.assert_called_with(SOUNDS_DIR / "invalid.mp3")
    
    @patch('voice._play_async')
    def test_begin_game(self, mock_play_async):
        """Test that _begin_game calls _play_async with the correct sound file."""
        vsfx = VoiceSFX()
        vsfx._begin_game({"dummy": "data"})
        mock_play_async.assert_called_with(SOUNDS_DIR / "start_game.mp3")
    
    @patch('voice._play_async')
    def test_on_game_over(self, mock_play_async):
        """Test that _on_game_over calls _play_async with the correct sound file."""
        vsfx = VoiceSFX()
        vsfx._on_game_over({"dummy": "data"})
        mock_play_async.assert_called_with(SOUNDS_DIR / "game_over.wav")
    
    @patch('voice._play_async')
    def test_file_not_exists(self, mock_play_async):
        """Edge case - when the sound file doesn't exist."""
        # Mock Path.exists() to return False
        with patch.object(Path, 'exists', return_value=False):
            vsfx = VoiceSFX()
            vsfx._on_move({"dummy": "data"})
            
            # Verify _play_async isn't called because file doesn't exist
            mock_play_async.assert_not_called()
    
    @patch('threading.Thread')
    def test_play_async_creates_thread(self, mock_thread):
        """Test that _play_async creates a thread correctly."""
        # Mock Path.exists() to return True
        with patch.object(Path, 'exists', return_value=True):
            path = Path("dummy/path.wav")
            _play_async(path)
            
            # Verify Thread was created with correct parameters
            mock_thread.assert_called_once()
            args, kwargs = mock_thread.call_args
            self.assertEqual(kwargs['target'], playsound)
            self.assertEqual(kwargs['args'], (str(path),))
            self.assertTrue(kwargs['daemon'])
            
            # Verify thread was started
            mock_thread_instance = mock_thread.return_value
            mock_thread_instance.start.assert_called_once()
    
    @patch('bus.subscribe')
    def test_voice_subscribes_to_events(self, mock_subscribe):
        """Test that VoiceSFX constructor subscribes to all necessary events."""
        vsfx = VoiceSFX()
        
        # Verify subscribe was called 5 times (for each event)
        self.assertEqual(mock_subscribe.call_count, 5)
        
        # Verify correct events and corresponding functions were subscribed
        expected_calls = [
            call("piece_moved", vsfx._on_move),
            call("piece_captured", vsfx._on_capture),
            call("invalid_move", vsfx._on_invalid_move),
            call("game_start", vsfx._begin_game),
            call("game_over", vsfx._on_game_over)
        ]
        mock_subscribe.assert_has_calls(expected_calls, any_order=True)


if __name__ == '__main__':
    unittest.main()