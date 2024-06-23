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


def main():
    logger = logging.getLogger("entrypoint.rasterize")
    argparser = argparse.ArgumentParser(description='Transform 3D tiles to "sattelite" shots')
    argparser.add_argument('--root_dir', type=str, help='Input path for decompressed glb files', required=True)
    argparser.add_argument('--planar', type=str, help='Planar json file', required=True)
    argparser.add_argument('--output', type=str, help='Output path', default="output")

    args = argparser.parse_args()
    output_folder = Path(args.output) / "rasterized"
    root_dir = args.root_dir

    os.makedirs(output_folder, exist_ok=True)
    
    logger.info(f"loading tiles from {root_dir} using planar json {args.planar}")
    tiles = lct.TilesLoader.from_planar(root_dir, args.planar)
    logger.info(f"loaded {len(tiles.models)} tiles")
    # rasterize returns a generator of images
    for i, (rgb, _depth, transform) in enumerate(lct.split_images(tiles, 
                                count=None,
                                camera_step=50, 
                                image_size=1024, 
                                to_pillow=True, 
                                draw_axis=False)):
        rgb.save(output_folder / f"rgb_{i}.png")
        with open(output_folder / f"transform_{i}.json", "w") as f:
            json.dump(transform, f, indent=4)

    logger.info(f"done")


if __name__ == '__main__':
    main()
