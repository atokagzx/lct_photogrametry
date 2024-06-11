#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import lct_solution as lct


if __name__ == "__main__":
    tileset_filename = "Tile_p3646_p720_glb/tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    # tileset_filename = "mapk/mapk.json"
    # root_dir = "mapk"
    tiles = lct.TilesLoader(tileset_filename, root_dir)
    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    scene.add_geometry(tm.creation.axis(origin_size=5))
    scene.add_geometry(tm.creation.axis(origin_size=5, transform=tiles.origin_rotation))
    for tf in tiles._tfs:
        scene.add_geometry(tm.creation.axis(origin_size=1, transform=tf))
    scene.show()
