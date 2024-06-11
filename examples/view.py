#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import lct_solution as lct


if __name__ == "__main__":
    tileset_filename = "tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    tiles = lct.TilesLoader(root_dir, tileset_filename)
    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    scene.add_geometry(tm.creation.axis(origin_size=20))
    for tf in tiles._tfs:
        scene.add_geometry(tf)
    scene.show()
