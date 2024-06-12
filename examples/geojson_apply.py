#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import json
import tqdm
import lct_solution as lct
from lct_solution import (Primitive, Polygon, MultiPolygon, Point, PolygonSegment)


def process_geojson(geo_data, tileset):
    features = []
    for feature in tqdm.tqdm(geo_data['features']):
        try:
            primitive = Primitive(tileset, feature)
        except ValueError as e:
            print(f"Error processing feature: {e}")
            continue
        features.append(primitive)
    return features


category_colors = {
    # green
    "park": [0, 255, 0, 255],
    # yellow
    "footway": [255, 255, 0, 255],
    # black
    "building": [0, 0, 0, 255],
    # violet
    "barrier": [255, 0, 255, 255]
}



if __name__ == "__main__":
    tileset_filename = "tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    geojson_filename = "geo_classified_full.geojson"
    heght = 165
    # coords = [55.75873228450434, 37.58316666796509, 160.29468727577478]
    
    with open(geojson_filename) as f:
        geojson = json.load(f)
    

    tiles = lct.TilesLoader(root_dir, tileset_filename)

    features = process_geojson(geojson, tiles)

    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    total = 0
    for feature in features:
        if feature.category not in category_colors:
            continue
        color = category_colors[feature.category]
        mesh = feature.to_trimesh(color)
        if mesh is None:
            continue
        scene.add_geometry(mesh)
        total += 1
    print("total: ", total)
    # scene.add_geometry(tm.creation.axis(origin_size=1, transform=coords_tf))
    scene.add_geometry(tm.creation.axis(origin_size=5))
    # scene.apply_scale(0.1)
    scene.show()
