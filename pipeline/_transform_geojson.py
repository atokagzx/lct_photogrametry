#!/usr/bin/env python3

from lct_solution import GLBDecompress
import json
import logging
import os
import subprocess
import concurrent.futures
from pathlib import Path
import argparse
import sys
import tqdm

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

def main():
    logger = logging.getLogger("entrypoint.tfgeojson")
    argparser = argparse.ArgumentParser(description='Transform geojson 2D to 3D')
    argparser.add_argument('--root_dir', type=str, help='Input path for decompressed glb files', required=True)
    argparser.add_argument('--planar', type=str, help='Planar json file', required=True)
    argparser.add_argument('--input', type=str, help='2D geojson file', required=True)
    argparser.add_argument('--output', type=str, help='Output path', default="output")

    args = argparser.parse_args()
    output_folder = Path(args.output)
    input_geojson_filename = args.input
    root_dir = args.root_dir

    os.makedirs(output_folder, exist_ok=True)
    
    with open(input_geojson_filename) as f:
        geojson = json.load(f)

    logger.info(f"loading tiles from {root_dir} using planar json {input_geojson_filename}")
    tiles = lct.TilesLoader.from_planar(root_dir, args.planar)
    logger.info(f"loaded {len(tiles.models)} tiles")
    logger.info(f"processing geojson")
    features = lct.process_geojson(geojson, tiles, category_colors)
    logging.info("Saving output.geojson")
    data = {
        "type": "FeatureCollection",
        "crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
        "features": []}
    for feature in features:
        if feature.category not in category_colors:
            continue
        data["features"].append(feature.as_geojson())
    with open(output_folder / 'transformed.geojson', 'w') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    logging.info("done")


if __name__ == '__main__':
    main()
