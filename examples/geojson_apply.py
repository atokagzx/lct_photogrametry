#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import lct_solution as lct


if __name__ == "__main__":
    tileset_filename = "Tile_p3646_p720_glb/tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    coords = [55.75873228450434, 37.58316666796509, 160.29468727577478]

    tiles = lct.TilesLoader(tileset_filename, root_dir)
    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    coords_tf = tiles.cartesian_to_tf(coords)
    scene.add_geometry(tm.creation.axis(origin_size=1, transform=coords_tf))
    scene.add_geometry(tm.creation.axis(origin_size=5))
    scene.show()
