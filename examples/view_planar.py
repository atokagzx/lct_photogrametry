#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import lct_solution as lct
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tileset_filename = "decompressed.json"
    root_dir = "new_format"
    tiles = lct.TilesLoader.from_planar(root_dir, tileset_filename)
    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    scene.add_geometry(tm.creation.axis(origin_size=20))
    for tf in tiles._tfs:
        scene.add_geometry(tf)
    scene.show()
