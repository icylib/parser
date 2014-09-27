
import icylib.model as model

__all__ = [
    "model",
    "open_library",
]

def open_library(base_dir):
    return model.Library(base_dir)
