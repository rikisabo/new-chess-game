import unittest
from unittest.mock import patch
import sys
import os
import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoreboard import ScoreBoard

class TestScoreBoard(unittest.TestCase):
    def setUp(self):
        """Initialize scoreboard and reset scores for each test."""
        self.sb = ScoreBoard()
        self.sb.scores = {"WHITE": 0, "BLACK": 0}
    
    def test_update_score_white(self):
        """Test that WHITE score increases when white piece captures."""
        dummy_piece = type("DummyPiece", (), {"id": "WP1"})
        data = {"winner": dummy_piece()}
        self.sb._update_score(data)
        self.assertEqual(self.sb.scores["WHITE"], 1)
        self.assertEqual(self.sb.scores["BLACK"], 0)
    
    def test_update_score_black(self):
        """Test that BLACK score increases when black piece captures."""
        dummy_piece = type("DummyPiece", (), {"id": "BP1"})
        data = {"winner": dummy_piece()}
        self.sb._update_score(data)
        self.assertEqual(self.sb.scores["BLACK"], 1)
        self.assertEqual(self.sb.scores["WHITE"], 0)
    
    def test_update_score_none_winner(self):
        """Edge case - when winner is None."""
        data = {"winner": None}
        # Expect no exception and no score change
        self.sb._update_score(data)
        self.assertEqual(self.sb.scores["WHITE"], 0)
        self.assertEqual(self.sb.scores["BLACK"], 0)
    
    def test_update_score_missing_winner(self):
        """Edge case - when winner key is missing from data."""
        data = {"something_else": "value"}
        # Expect no exception and no score change
        self.sb._update_score(data)
        self.assertEqual(self.sb.scores["WHITE"], 0)
        self.assertEqual(self.sb.scores["BLACK"], 0)
    
    def test_update_score_invalid_id(self):
        """Edge case - when winner id format is invalid."""
        # Object with non-standard id format
        dummy_piece = type("DummyPiece", (), {"id": "XYZ"})
        data = {"winner": dummy_piece()}
        # Expect no exception and no score change
        self.sb._update_score(data)
        self.assertEqual(self.sb.scores["WHITE"], 0)
        self.assertEqual(self.sb.scores["BLACK"], 0)
    
    def test_high_score(self):
        """Test case - very high score accumulation."""
        # Simulate capturing many pieces
        dummy_piece = type("DummyPiece", (), {"id": "WP1"})
        data = {"winner": dummy_piece()}
        
        # Capture 1000 pieces
        for _ in range(1000):
            self.sb._update_score(data)
        
        self.assertEqual(self.sb.scores["WHITE"], 1000)
        self.assertEqual(self.sb.scores["BLACK"], 0)
    
    @patch('cv2.putText')
    def test_draw_method(self, mock_putText):
        """Test that the draw method renders correctly."""
        # Prepare empty image
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        origin = (10, 20)
        player = "WHITE"
        
        # Set a score
        self.sb.scores["WHITE"] = 42
        
        # Call the draw method
        self.sb.draw(img, origin, player)
        
        # Verify that cv2.putText was called with correct parameters
        mock_putText.assert_called_once()
        args, _ = mock_putText.call_args
        self.assertEqual(args[0].all(), img.all())  # Check that image is the same
        self.assertEqual(args[1], "WHITE: 42")  # Check correct text
        self.assertEqual(args[2], origin)  # Check correct position


if __name__ == '__main__':
    unittest.main()