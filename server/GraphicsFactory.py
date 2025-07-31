import pathlib

# from Graphics import Graphics  # Not needed for server
from img import Img
from mock_img import MockImg


class ImgFactory:
    def __call__(self, *args, **kwargs):
        # f = img_factory()
        # img = f(path, size, keep_aspect)
        # Accept both positional and keyword keep_aspect
        path = args[0]
        size = args[1]
        keep_aspect = kwargs.get("keep_aspect", args[2] if len(args) >= 3 else False)
        return Img().read(path, size, keep_aspect)

class MockImgFactory(ImgFactory):
    def __call__(self, *args, **kwargs):
        path = args[0]
        size = args[1]
        keep_aspect = kwargs.get("keep_aspect", args[2] if len(args) >= 3 else False)
        return MockImg().read(path, size, keep_aspect)


class GraphicsFactory:

    def __init__(self, img_factory):
        # callable path, cell_size, keep_aspect -> Img
        self._img_factory = img_factory

    def load(self,
             sprites_dir: str,
             cfg: dict,
             cell_size: tuple[int, int]) -> object:
        # Server doesn't need graphics - return a mock graphics object
        return MockGraphics()

    def create_graphics(self, board_size: tuple[int, int], 
             cell_size: tuple[int, int]) -> object:
        # Server doesn't need graphics - return None
        return None


class MockGraphics:
    """Mock graphics object for server use"""
    def __init__(self):
        pass
        
    def __getattr__(self, name):
        # Return a no-op function for any method call
        return lambda *args, **kwargs: None
