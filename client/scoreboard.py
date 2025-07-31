from collections import defaultdict
import cv2
from enums.EventType import EventType
from message_bus import subscribe

class ScoreBoard:
    """
    Displays and updates the game scoreboard.
    """
    def __init__(self):
        # Initialize scores for each player
        self.scores = {"WHITE": 0, "BLACK": 0}
        subscribe(EventType.PIECE_CAPTURED, self._update_score)

    def _update_score(self, data):
        # Increment the winner's score when a piece is captured.
        winner = data.get("winner")
        if winner:
            if winner.id[1] == "W":
                self.scores["WHITE"] += 1
            else:
                self.scores["BLACK"] += 1

    def draw(self, img, origin, player):
        """
        Draw the scoreboard for the given player at the specified origin.
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        text = f"{player}: {self.scores[player]}"
        cv2.putText(img, text, origin, font, 1, (255, 255, 255), 2, cv2.LINE_AA)
