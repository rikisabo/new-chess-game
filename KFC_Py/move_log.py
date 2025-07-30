from enums.EventType import EventType
from message_bus import subscribe
import time
import cv2

MAX_ROWS = 8  # Maximum number of recent moves displayed per player
ROW_HEIGHT = 22  # Row height in pixels

class MoveLog:
    """
    Records every move and can draw a graphical table on screen.
    """
    def __init__(self):
        self.moves = {"WHITE": [], "BLACK": []}
        subscribe(EventType.PIECE_MOVED, self._record)

    def _record(self, data):
        piece_id = data["piece_id"]
        player = "WHITE" if piece_id[1] == "W" else "BLACK"
        current_time = time.strftime("%H:%M:%S", time.localtime())
        self.moves[player].append((current_time, piece_id))
        for key in ("WHITE", "BLACK"):
            self.moves[key] = self.moves[key][-MAX_ROWS:]

    def draw(self, img, origin=(1660, 30), player="WHITE"):
        """
        Draw the moves table on the left or right side with a white background and black text.
        """
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale, thickness = 0.5, 1
        x0, y0 = origin
        width, height = 250, 1080 - 60

        # Draw white background
        cv2.rectangle(img, (x0 - 10, y0 - 30), (x0 + width, y0 + height), (255, 255, 255), -1)
        # Title
        cv2.putText(img, f"{player} Moves", (x0 + 10, y0), font, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
        y0 += ROW_HEIGHT
        cv2.putText(img, "Time       Move", (x0 + 10, y0), font, scale, (0, 0, 0), thickness, cv2.LINE_AA)
        y0 += ROW_HEIGHT
        for t, m in self.moves[player]:
            cv2.putText(img, f"{t}  {m}", (x0 + 10, y0), font, scale, (0, 0, 0), thickness, cv2.LINE_AA)
            y0 += ROW_HEIGHT
