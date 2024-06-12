#!/usr/bin/env python3

import logging
import os
from pathlib import Path
import json
import matplotlib.pyplot as plt
import lct_solution as lct


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tileset_filename = "tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    save_dir = Path("out_img")
    os.makedirs(save_dir, exist_ok=True)
    tiles = lct.TilesLoader.from_tileset(root_dir, tileset_filename)
    meshes = tiles.models.values()
    splitted = lct.split_images(tiles, 
                                (4, 4), 
                                camera_step=50, 
                                image_size=1000, 
                                to_pillow=True, 
                                draw_axis=False)
    for i, (rgb, depth, transform) in enumerate(splitted):
        rgb.save(save_dir / f"rgb_{i}.png")
        depth.save(save_dir / f"depth_{i}.png")
        with open(save_dir / f"transform_{i}.json", "w") as f:
            json.dump(transform, f, indent=4)
    if False:
        plt.figure()
        for i, (rgb, depth, transform) in enumerate(splitted):
            plt.subplot(2, 2, i + 1)
            plt.imshow(rgb)
            plt.axis("off")
        plt.show()
        plt.figure()
        for i, (rgb, depth, transform) in enumerate(splitted):
            plt.subplot(2, 2, i + 1)
            plt.imshow(depth)
            plt.axis("off")
        plt.show()