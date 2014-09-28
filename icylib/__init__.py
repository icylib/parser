
import icylib.model as model
import icylib.exporter as exporter

__all__ = [
    "model",
    "exporter",
    "open_library",
]

def open_library(base_dir):
    return model.Library(base_dir)
