import pyassimp
import open3d as o3d
import trimesh as tm
import numpy as np
import PIL
import pathlib
import json

from gltflib.gltf import GLTF
from .glb import glb_to_pillow
import json
from dataclasses import dataclass
from trimesh import creation, transformations
import pyrender
import matplotlib.pyplot as plt
import tqdm

from ._datatypes import (Tile, 
                         transform_mtx)
from ._utils import compute_origin

class TilesLoader:
    def __init__(self, tileset_filename, root_dir):
        self._origin_translation = None
        root_dir = pathlib.Path(root_dir)
        with open(tileset_filename) as f:
            tileset = json.load(f)
        self._tiles = []
        root = tileset['root']
        self._get_child(root, 0)
        self._tfs = []
        self._origin_rotation = compute_origin(self._tiles)
        self._origin_translation = None
        self._find_corner()
        self._loaded_models = {}
        for tile in tqdm.tqdm(self._tiles, desc="Loading .glb models"):
            if tile.uri not in self._loaded_models:
                trimeshes = self.load_model(root_dir / tile.uri)
                if self._origin_translation is None:
                    print("Warning: origin translation is not set")
                    origin_translation = np.eye(4)
                    origin_translation[:3, 3] = tile.box[:3]
                    self._origin_translation = origin_translation
                for mesh in trimeshes:
                    mesh.apply_transform(transform_mtx)
                    box_translation = np.eye(4)
                    box_translation[:3, 3] = tile.box[:3]
                    mesh.apply_transform(np.linalg.inv(self._origin_translation) @ box_translation)
                    self._tfs.append(np.linalg.inv(self._origin_translation) @ box_translation)
                self._loaded_models[tile.uri] = trimeshes
                
    
    def _get_child(self, a, level):
        if 'children' not in a:
            if 'content' in a:
                uri = a['content']['uri']
                bounding_volume = np.array(a['boundingVolume']['box'])
                geometric_error = a['geometricError']
                tile = Tile(uri, bounding_volume, geometric_error)
                self._tiles.append(tile)
            return
        for i in a['children']:
            self._get_child(i, level + 1)


    def _find_corner(self):
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        print("rot: ", self._origin_rotation)
        for tile in self._tiles[:5]:
            box_translation = np.eye(4)
            box_translation[:3, 3] = tile.box[:3]
            box_translation = self._origin_rotation @ box_translation
            if box_translation[0, 3] < min_x:
                min_x = box_translation[0, 3]
            if box_translation[1, 3] < min_y:
                min_y = box_translation[1, 3]
            if box_translation[2, 3] < min_z:
                min_z = box_translation[2, 3]
            if box_translation[0, 3] > max_x:
                max_x = box_translation[0, 3]
            if box_translation[1, 3] > max_y:
                max_y = box_translation[1, 3]
            if box_translation[2, 3] > max_z:
                max_z = box_translation[2, 3]
        origin_translation = np.eye(4)
        origin_translation[:3, 3] = [min_x, min_y, min_z]
        origin_translation = np.linalg.inv(self._origin_rotation) @ origin_translation
        self._origin_translation = np.eye(4)
        self._origin_translation[:3, 3] = origin_translation[:3, 3]
        

    @staticmethod
    def load_model(path: pathlib.Path):
        trimeshes = []
        base_path = pathlib.Path(path).parent
        if not pathlib.Path(path).exists():
            raise FileNotFoundError(f"File not found: {path}")
        with pyassimp.load(str(path)) as scene:
            if path.suffix == ".glb":
                gltf: GLTF = GLTF.load(path)
                images = glb_to_pillow(gltf, save=False)
            else:
                images = None
            for index, mesh in enumerate(scene.meshes):
                vertices = mesh.vertices
                faces = mesh.faces
                material = mesh.material
                if images is None:
                    webp_texture = material.properties.get(('file', 1))
                    texture = None
                    if webp_texture is not None:
                        img = PIL.Image.open(base_path / webp_texture)
                        uvs = mesh.texturecoords[0]
                        material = tm.visual.texture.SimpleMaterial(image=img)
                        texture = tm.visual.TextureVisuals(uv=uvs, image=img, material=material)
                else:
                    img = images[index]
                    uvs = mesh.texturecoords[0]
                    material = tm.visual.texture.SimpleMaterial(image=img)
                    texture = tm.visual.TextureVisuals(uv=uvs, image=img, material=material)
                trim = tm.Trimesh(vertices=vertices, faces=faces, visual=texture)
                trim.fix_normals()

                trimeshes.append(trim)
            return trimeshes
        
    
    @property
    def models(self):
        return self._loaded_models
    

    @property
    def tiles(self):
        return tuple(self._tiles)
    

    @property
    def origin_rotation(self):
        return self._origin_rotation
    

    @property
    def origin_translation(self):
        return self._origin_translation
    

    def get_transformed_meshes(self):
        origin = None
        meshes = []
        for tile in self.tiles:
            trimeshes = self.models[tile.uri]
            for mesh in trimeshes:
                mesh.apply_transform(tm.transformations.translation_matrix(tile.box[:3]))
                if origin is None:
                    origin = tile.box[:3]
                mesh.apply_transform(tm.transformations.translation_matrix(tile.box[:3] - origin))
                meshes.append(mesh)
        return meshes