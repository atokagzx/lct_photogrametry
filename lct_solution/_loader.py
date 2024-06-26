import pyassimp
import trimesh as tm
import numpy as np
import PIL
import pathlib
import json

from gltflib.gltf import GLTF
from .glb import glb_to_pillow
import json
import matplotlib.pyplot as plt
import tqdm
import glob
import logging
from ._datatypes import (Tile, 
                         transform_mtx)
from ._utils import compute_origin
from ._geography import (cartesian_to_wsg84,
                            wsg84_to_cartesian)


class TilesLoader:
    def __init__(self, root_dir):
        self._logger = logging.getLogger("tiles_loader")
        self._origin_translation = None
        root_dir = pathlib.Path(root_dir)
        self._root_dir = root_dir
        self._tiles = []
        

    def _load(self, root_dir):
        self._tfs = []
        self._origin_rotation = compute_origin(self._tiles)
        self._logger.info(f"origin rotation: {self._origin_rotation}")
        self._find_corner()
        self._logger.info(f"origin translation: {self._origin_translation}")
        self._loaded_models = {}
        for tile in tqdm.tqdm(self._tiles, desc="Loading .glb models", unit="tile", leave=True):
            if tile.uri not in self._loaded_models:
                try:
                    trimeshes = self.load_model(root_dir / tile.uri)
                except (pyassimp.errors.AssimpError, FileNotFoundError) as e:
                    self._logger.exception(f"error loading tile {tile.uri}")
                    continue
                for mesh in trimeshes:
                    mesh.apply_transform(transform_mtx)
                    box_translation = np.eye(4)
                    box_translation[:3, 3] = tile.box[:3]
                    mesh.apply_transform(np.linalg.inv(self.origin_translation) @ np.linalg.inv(self.origin_rotation)  @ box_translation)
                    tf = tm.creation.axis(origin_size=1)
                    tf.apply_transform(np.linalg.inv(self.origin_translation) @ np.linalg.inv(self.origin_rotation)  @ box_translation)
                    self._tfs.append(tf)
                self._loaded_models[tile.uri] = trimeshes


    @classmethod
    def from_planar(cls, root_dir, root_tileset_filename) -> 'TilesLoader':
        '''
        Load tiles from a planar json file
        @param root_dir: root directory of the tileset
        @param root_tileset_filename: filename of the tileset, should be a json file at the root of the tileset
        '''
        loader = cls(root_dir)
        with open(loader._root_dir / root_tileset_filename) as f:
            tileset = json.load(f)
        for tile in tileset['data']:
            box = np.array(tile['boundingVolume']['box'])
            geometric_error = None
            uri = tile['content']['uri']
            tile = Tile(uri, box, geometric_error)
            loader._tiles.append(tile)
        loader._load(loader._root_dir)
        return loader


    @classmethod
    def from_tileset(cls, root_dir, root_tileset_filename) -> 'TilesLoader':
        '''
        Recursively load tiles from a tileset
        @param root_dir: root directory of the tileset
        @param root_tileset_filename: filename of the tileset, should be a json file at the root of the tileset
        '''
        loader = cls(root_dir)
        with open(loader._root_dir / root_tileset_filename) as f:
            root_tileset = json.load(f)
        loader._get_child(root_tileset['root'], 0)
        loader._load(loader._root_dir)
        return loader


    def _get_child(self, a, level):
        if 'content' in a:
            uri = a['content']['uri']
            if uri.endswith('.json'):
                include_file = self._root_dir / uri
                self._logger.info(f"loading additional tileset: {include_file}")
                with open(include_file) as f:
                    a = json.load(f)
                self._get_child(a['root'], level + 1)
            else:
                if 'children' not in a:
                    bounding_volume = np.array(a['boundingVolume']['box'])
                    geometric_error = a['geometricError']
                    tile = Tile(uri, bounding_volume, geometric_error)
                    self._tiles.append(tile)
        if 'children' in a:
            for i in a['children']:
                self._get_child(i, level + 1)


    def _find_corner(self):
        min_x = min_y = min_z = float('inf')
        max_x = max_y = max_z = float('-inf')
        # scene = tm.Scene()
        for tile in self._tiles:
            box_translation = np.eye(4)
            box_translation[:3, 3] = tile.box[:3]
            # box_translation = self._origin_rotation @ box_translation
            box_translation = np.linalg.inv(self.origin_rotation) @ box_translation
            # scene.add_geometry(tm.creation.axis(origin_size=1, transform=box_translation))
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
        self._origin_translation = origin_translation
        self._min_height = self.tf_to_cartesian(np.eye(4))[-1]
        self._logger.info(f"min height: {self._min_height}")
        # compute max point
        max_point = np.eye(4)
        max_point[:3, 3] = [max_x, max_y, max_z]
        self._max_point = max_point


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
    

    @property
    def min_height(self):
        return self._min_height
    

    @property
    def max_point(self):
        '''
        Represents the maximum point in the scene
        '''
        return self._max_point
    

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
    

    def cartesian_to_tf(self, coords: list):
        if len(coords) != 3:
            raise ValueError(f"Expected 3 coordinates, got {coords}")
        pos = cartesian_to_wsg84(*coords)
        coors_tf = np.eye(4)
        coors_tf[:3, 3] = pos
        coords_tf = np.linalg.inv(self.origin_translation) @ np.linalg.inv(self.origin_rotation) @ coors_tf @ self.origin_rotation
        return coords_tf
    

    def tf_to_cartesian(self, tf):
        pos = np.linalg.inv(np.linalg.inv(self.origin_translation) @ np.linalg.inv(self.origin_rotation)) @ tf
        return wsg84_to_cartesian(pos[0, 3], pos[1, 3], pos[2, 3])
    