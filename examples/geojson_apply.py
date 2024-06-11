#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import json
import lct_solution as lct


if __name__ == "__main__":
    tileset_filename = "Tile_p3646_p720_glb/tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    geojson_filename = "geo_classified_full.geojson"
    heght = 165
    # coords = [55.75873228450434, 37.58316666796509, 160.29468727577478]
    
    with open(geojson_filename) as f:
        geojson = json.load(f)
    coords = []
    for feature in geojson['features']:
        if feature['properties']['class'] == "park":
            for point in feature['geometry']['coordinates']:
                for p in point:
                    if isinstance(p[0], list):
                        print("Skip")
                        continue
                    if len(p) == 3:
                        coord = [p[1], p[0], p[2]]
                    elif len(p) == 2:
                        coord = [p[1], p[0], heght]
                    else:
                        raise ValueError(f"Wrong point format: {p}")
                    coords.append(coord)
        # elif feature['geometry']['type'] == 'Polygon':
        #     for point in feature['geometry']['coordinates'][0]:
        #         coords.append(point)
    print(f"Found {len(coords)} points in geojson")
    tiles = lct.TilesLoader(tileset_filename, root_dir)
    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    total = 0
    bounds = [
        [-100, 700],
        [-100, 700],
        [-100, 700]
    ]
    for coord in coords:
        coords_tf = tiles.cartesian_to_tf(coord)
        x, y, z = coords_tf[:3, 3]
        if not all([bounds[i][0] < coords_tf[i, 3] < bounds[i][1] for i in range(3)]):
            continue
        total += 1
        scene.add_geometry(tm.creation.axis(origin_size=0.5, transform=coords_tf))
    print("total: ", total)
    # scene.add_geometry(tm.creation.axis(origin_size=1, transform=coords_tf))
    scene.add_geometry(tm.creation.axis(origin_size=5))
    scene.show()
