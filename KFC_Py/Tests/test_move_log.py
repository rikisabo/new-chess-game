import unittest
from unittest.mock import patch
import sys
import os
import cv2
import numpy as np

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from move_log import MoveLog

class TestMoveLog(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.move_log = MoveLog()
    
    def test_record_white_move(self):
        """Test recording a white piece movement."""
        data = {"piece_id": "WP1", "target_cell": (3, 4)}
        self.move_log._record(data)
        self.assertEqual(len(self.move_log.moves["WHITE"]), 1)
        self.assertEqual(len(self.move_log.moves["BLACK"]), 0)
        self.assertEqual(self.move_log.moves["WHITE"][0][1], "WP1")
    
    def test_record_black_move(self):
        """Test recording a black piece movement."""
        data = {"piece_id": "BP1", "target_cell": (3, 4)}
        self.move_log._record(data)
        self.assertEqual(len(self.move_log.moves["BLACK"]), 1)
        self.assertEqual(len(self.move_log.moves["WHITE"]), 0)
        self.assertEqual(self.move_log.moves["BLACK"][0][1], "BP1")
    
    def test_record_invalid_piece_id(self):
        """Test handling of an invalid piece ID."""
        data = {"piece_id": "XYZ", "target_cell": (3, 4)}
        self.move_log._record(data)
        # Expect no records added for invalid piece ID
        self.assertEqual(len(self.move_log.moves["WHITE"]), 0)
        self.assertEqual(len(self.move_log.moves["BLACK"]), 0)
    
    def test_record_multiple_moves(self):
        """Test recording multiple moves and verify max rows limit."""
        # Add more than MAX_ROWS moves
        for i in range(12):  # Assuming MAX_ROWS = 8
            data = {"piece_id": f"WP{i}", "target_cell": (3, 4)}
            self.move_log._record(data)
        
        # Verify only most recent MAX_ROWS are kept
        from move_log import MAX_ROWS
        self.assertEqual(len(self.move_log.moves["WHITE"]), MAX_ROWS)
        self.assertEqual(self.move_log.moves["WHITE"][-1][1], "WP11")  # Last added piece
    
    @patch('cv2.putText')
    @patch('cv2.rectangle')
    def test_draw_method(self, mock_rectangle, mock_putText):
        """Test the draw method renders correctly."""
        # Create image and add some moves
        img = np.zeros((200, 200, 3), dtype=np.uint8)
        data = {"piece_id": "WP1", "target_cell": (3, 4)}
        self.move_log._record(data)
        
        # Call draw method
        self.move_log.draw(img, origin=(10, 20), player="WHITE")
        
        # Verify rectangle was drawn for background
        mock_rectangle.assert_called_once()
        
        # Verify putText was called at least twice (header + move entry)
        self.assertGreaterEqual(mock_putText.call_count, 2)


if __name__ == '__main__':
    unittest.main()