#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import lct_solution as lct


if __name__ == "__main__":
    tileset_filename = "tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    tiles = lct.TilesLoader(root_dir, tileset_filename)
    meshes = tiles.models.values()
    point = [30, 30, 0]
    direction = [0, 0, 1]

    intersections = []
    for mesh in meshes:
        for m in mesh:
            intersector = tm.ray.ray_pyembree.RayMeshIntersector(m)
            locations, index_ray, index_tri = intersector.intersects_location([point], [direction])
            if len(locations) > 0:
                intersections.append(locations[0])
    print(intersections)
    scene = tm.Scene(meshes)
    scene.add_geometry(tm.creation.axis(origin_size=20))
    for tf in tiles._tfs:
        scene.add_geometry(tf)
    for i in intersections:
        point = np.eye(4)
        point[:3, 3] = i
        scene.add_geometry(tm.creation.axis(origin_size=4, transform=point))
        
    scene.show()
