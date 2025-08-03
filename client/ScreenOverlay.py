import cv2
import numpy as np
from enums.EventType import EventType
from message_bus import subscribe
import time

class ScreenOverlay:
    def __init__(self, window_name="Game"):
        # Subscribe to game start and game over events
        subscribe(EventType.GAME_START, self.on_game_start)
        subscribe(EventType.GAME_END, self.on_game_over)

        self.duration = 3000  # Display duration in milliseconds
        self.window_name = window_name  # שמירת שם החלון שהועבר
        self.canvas_width = 1920
        self.canvas_height = 1080
        
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.text_scale = 2
        self.text_thickness = 3
        self.margin = 20  # Margin between text and image

    def on_game_start(self, data):
        # Show welcome message overlay with welcome image
        welcome_message = "Welcome to the ChessGame!"
        welcome_img_path = "../pieces/welcome_picture.jpg"
        self._show_overlay(welcome_message, welcome_img_path)

    def on_game_over(self, data):
        # Show game over message overlay with game over image
        game_over_message = "Game Over! Thanks for playing!"
        game_over_img_path = "../pieces/gameover_picture.jpg"
        self._show_overlay(game_over_message, game_over_img_path)

    def _create_canvas(self) -> np.ndarray:
        """
        Create a blank canvas with a black background.
        """
        return np.zeros((self.canvas_height, self.canvas_width, 3), dtype=np.uint8)

    def _draw_centered_text(self, img: np.ndarray, text: str) -> tuple:
        """
        Draw centered text on the given canvas.
        Returns a tuple with the text size and the y-coordinate of the text.
        """
        text_size, _ = cv2.getTextSize(text, self.font, self.text_scale, self.text_thickness)
        text_x = (self.canvas_width - text_size[0]) // 2
        text_y = self.canvas_height // 4  # Place text at 1/4th of the canvas height
        cv2.putText(img, text, (text_x, text_y), self.font, self.text_scale, (255, 255, 255), self.text_thickness, cv2.LINE_AA)
        return text_size, text_y

    def _load_and_resize_image(self, image_path: str, desired_width: int) -> np.ndarray:
        """
        Load an image from the given path and resize it to the desired width while maintaining aspect ratio.
        """
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            return None
        scale_factor = desired_width / img.shape[1]
        new_width = int(img.shape[1] * scale_factor)
        new_height = int(img.shape[0] * scale_factor)
        return cv2.resize(img, (new_width, new_height))

    def _show_overlay(self, text: str, image_path: str):
        """
        Create and display an overlay on the game window containing centered text and an image positioned below the text.
        """
        canvas = self._create_canvas()
        text_size, text_y = self._draw_centered_text(canvas, text)
        
        # Load the overlay image; set desired width to half the canvas width
        desired_width = self.canvas_width // 2
        overlay_image = self._load_and_resize_image(image_path, desired_width)
        if overlay_image is not None:
            new_height, new_width = overlay_image.shape[:2]
            # Position the image below the text with a defined margin
            image_y = text_y + text_size[1] + self.margin
            # Ensure the image does not exceed the available space
            available_space = self.canvas_height - image_y
            if new_height > available_space:
                scale_factor = available_space / new_height
                new_height = int(new_height * scale_factor)
                new_width = int(new_width * scale_factor)
                overlay_image = cv2.resize(overlay_image, (new_width, new_height))
            image_x = (self.canvas_width - new_width) // 2
            # Place the overlay image onto the canvas
            canvas[image_y:image_y+new_height, image_x:image_x+new_width] = overlay_image

        cv2.imshow(self.window_name, canvas)
        cv2.waitKey(self.duration)