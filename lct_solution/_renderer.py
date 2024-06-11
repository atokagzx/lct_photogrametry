import typing
import trimesh as tm
import numpy as np
import pyrender
import PIL
import os
from pathlib import Path
import json
import tqdm
import matplotlib.pyplot as plt
from ._loader import TilesLoader


def split_images(tiles: TilesLoader,
                count: typing.Tuple[int, int], 
                camera_step: float = 50, 
                image_size: int = 1000,
                light_intensity: float = 10.0,
                to_pillow: bool = False,
                draw_axis: bool = False,
                camera_dst: float = 100):
    '''
    Split images into count * count grid
    @param tiles: instance of TilesLoader
    @param count: tuple of two integers, number of images in x and y axes
    @param camera_step: step of the camera (meters)
    @param image_size: size of the image (pixels)
    @param light_intensity: intensity of the light
    @param draw_axis: draw axis on the image
    @param camera_dst: distance from the camera to the origin
    @return: list of tuples (rgb, depth, transform)
    '''
    splitted = []
    for x in tqdm.tqdm(range(count[0]), desc="Generating images in x"):
        for y in tqdm.tqdm(range(count[1]), desc="Generating images in y", leave=False):
            scene = pyrender.Scene()
            for mesh in tiles._loaded_models.values():
                mesh = pyrender.Mesh.from_trimesh(mesh, smooth=False)
                scene.add(mesh)
            camera_tf = np.eye(4)
            camera_tf[:3, 3] = [camera_step / 2 + x * camera_step, camera_step / 2 + y * camera_step, camera_dst]
            # camera_tf = np.dot(tiles.origin_rotation, camera_tf)
            camera_axis_frame = tm.creation.axis(origin_size=5, transform=camera_tf)
            scene.add(pyrender.Mesh.from_trimesh(camera_axis_frame, smooth=False))
            
            if draw_axis:
                temp_tf = np.eye(4)
                temp_tf[:3, 3] = [0, 0, -10]
                temp_tf = np.dot(camera_tf, temp_tf)
                camera_axis_frame = tm.creation.axis(origin_size=2, transform=temp_tf)
                scene.add(pyrender.Mesh.from_trimesh(camera_axis_frame, smooth=False))

            # add camera
            camera = pyrender.OrthographicCamera(xmag=1.0, ymag=camera_step / 2, znear=0.1, zfar=1000) 
            scene.add(camera, pose=camera_tf)
            light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=light_intensity)

            scene.add(light, pose=camera_tf)
            renderer = pyrender.OffscreenRenderer(image_size, image_size)
            color, depth = renderer.render(scene)
            if to_pillow:
                color = PIL.Image.fromarray(color, "RGB")
                depth = PIL.Image.fromarray((depth * 255).astype(np.uint8), "L")
            renderer.delete()
            # save as image
            transform = {
                "tf": (tiles.origin_translation @ tiles.origin_rotation @ camera_tf).tolist(),
                "step_m": camera_step,
                "image_size": image_size,
                "camera_dst": camera_dst,
            }
            splitted.append((color, depth, transform))
    return splitted
