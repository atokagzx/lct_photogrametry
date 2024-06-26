#!/usr/bin/env python3

import trimesh as tm
import open3d as o3d
import numpy as np
import logging
import lct_solution as lct


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    # tileset_filename = "tileset_box_b3dm_crop.json"
    # root_dir = "Tile_p3646_p720_glb"
    # tiles = lct.TilesLoader.from_tileset(root_dir, tileset_filename)
    tileset_filename = "decompressed.json"
    root_dir = "new_format"
    tiles = lct.TilesLoader.from_planar(root_dir, tileset_filename)
    meshes = tiles.models.values()
    # meshes = tiles.models.values()
    o3d_meshes = []
    for i in meshes:
        for j in i:
            o3d_mesh = j.as_open3d
            o3d_meshes.append(o3d_mesh)

    o3d.visualization.draw_geometries(o3d_meshes)
    