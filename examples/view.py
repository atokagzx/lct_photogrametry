#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import lct_solution as lct
import logging


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tileset_filename = "tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    tiles = lct.TilesLoader.from_tileset(root_dir, tileset_filename)
    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    scene.add_geometry(tm.creation.axis(origin_size=20))
    # for tf in tiles._tfs:
    #     scene.add_geometry(tf)
    for tile in tiles.tiles:
        sphere = tile.box # xyzr
        radius = sphere[3]

        tf = np.eye(4)
        tf[:3, 3] = sphere[:3]
        tf = np.linalg.inv(tiles.origin_translation) @ np.linalg.inv(tiles.origin_rotation) @ tf
        sphere_geom = tm.creation.icosphere(radius=radius, transform=tf)
        sphere_geom.visual.face_colors = [255, 0, 0, 100]
        print(tf)
        scene.add_geometry(sphere_geom)
        center = tf[:3, 3]

        corners = [[center[0] + radius, center[1] + radius, center[2] + radius],
                   [center[0] + radius, center[1] + radius, center[2] - radius],
                   [center[0] + radius, center[1] - radius, center[2] + radius],
                   [center[0] + radius, center[1] - radius, center[2] - radius],
                   [center[0] - radius, center[1] + radius, center[2] + radius],
                   [center[0] - radius, center[1] + radius, center[2] - radius],
                   [center[0] - radius, center[1] - radius, center[2] + radius],
                   [center[0] - radius, center[1] - radius, center[2] - radius]]
        # apply transformation matrix to the corners
        for i in range(8):
            corner = np.eye(4)
            corner[:3, 3] = corners[i]
            scene.add_geometry(tm.creation.axis(origin_size=1, transform=corner))
            
    scene.show()
