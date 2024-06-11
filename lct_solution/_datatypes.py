import numpy as np
from dataclasses import dataclass


transform_mtx = [
    [1.0, 0.0,  0.0, 0.0],
    [0.0, 0.0, -1.0, 0.0],
    [0.0, 1.0,  0.0, 0.0],
    [0.0, 0.0,  0.0, 1.0]]


@dataclass
class Tile:
    uri: str
    # group: str
    box: np.ndarray
    geometric_error: float
