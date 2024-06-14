#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import json
import tqdm
import logging
import lct_solution as lct
from lct_solution._datatypes import EmptyPolygon
from lct_solution import (Primitive, 
    Polygon, 
    MultiPolygon, 
    Point, 
    PolygonSegment)


category_colors = {
    # green
    "park": [0, 255, 0, 200],
    # yellow
    "footway": [255, 255, 0, 200],
    # violet
    "barrier": [255, 0, 255, 200],
    # black
    "road": [0, 0, 0, 200],
    # blue
    "water": [0, 0, 255, 200],
    # gray
    "historic": [128, 128, 128, 200]
}


def process_geojson(geo_data, tileset):
    features = []
    for feature in tqdm.tqdm(geo_data['features'], desc="Processing features"):
        if feature['properties']['class'] not in category_colors.keys():
            continue
        try:
            primitive = Primitive(tileset, feature)
        except EmptyPolygon as e:
            continue
        except Exception as e:
            logging.exception(f"error processing feature: {e}")
            continue
        features.append(primitive)
    return features


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tileset_filename = "tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    geojson_filename = "geo_classified_full.geojson"

    with open(geojson_filename) as f:
        geojson = json.load(f)

    tiles = lct.TilesLoader.from_tileset(root_dir, tileset_filename)

    features = process_geojson(geojson, tiles)

    meshes = tiles.models.values()
    if True:
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
        logging.info(f"Total features added: {total}")
        scene.add_geometry(tm.creation.axis(origin_size=5))
        scene.show()
    logging.info("Saving output.geojson")
    data = {
        "type": "FeatureCollection",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
        "features": []}
    for feature in features:
        if feature.category not in category_colors:
            continue
        data["features"].append(feature.as_geojson())
    with open("output.geojson", "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
