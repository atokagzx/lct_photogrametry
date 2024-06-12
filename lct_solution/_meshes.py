import numpy as np
import trimesh as tm
from dataclasses import dataclass
import tqdm
from scipy.spatial import Delaunay
import traceback

class Point:
    def __init__(self, tileset, cartesian, default_height = 150):
        self._tileset = tileset
        self._cartesian = cartesian
        if len(cartesian) == 2:
            self._tf = self._tileset.cartesian_to_tf([cartesian[1], cartesian[0], default_height])
        elif len(cartesian) == 3:
            self._tf = self._tileset.cartesian_to_tf([cartesian[1], cartesian[0], cartesian[2]])
        else:
            raise ValueError(f"Wrong point format: {cartesian}")
        

    def to_trimesh(self, color=None):
        if color is None:
            color = [255, 0, 255, 255]
        mesh = tm.creation.axis(origin_size=1)
        mesh.apply_transform(self._tf)
        mesh.visual.face_colors = color
        return mesh
    

    @classmethod
    def from_tf(cls, tileset, tf):
        if tf.shape != (4, 4):
            raise ValueError(f"Wrong shape of transformation matrix: {tf.shape}")
        point = cls(tileset, [0, 0, 0])
        point._tf = tf
        return point


bounds = np.array([[-50, -50, 200], [500, 500, -200]])
class PolygonSegment:
    def __init__(self, tileset, points):
        self._tileset = tileset
        self._points = [Point(tileset, point) for point in points]
        self.find_real_height()


    def to_trimesh(self, color=None):
        if len(self._points) < 4:
            return None, None
        if color is None:
            color = [255, 0, 255, 80]
        points = [point._tf[:3, 3] for point in self._points]
        # check if any point is outside of the bounds
        for point in points:
            if point[0] < bounds[0, 0] or point[0] > bounds[1, 0] or point[1] < bounds[0, 1] or point[1] > bounds[1, 1]:
                return None, None
        try:
            tri = Delaunay([point[:2] for point in points])
        except Exception as e:
            traceback.print_exc()
            print(f"Error triangulating polygon: {e}. Points: {points}")
            return None, None
        faces = tri.simplices
        vertex_colors = np.array([color] * len(points), dtype=np.uint8)
        mesh = tm.Trimesh(vertices=points, faces=faces, vertex_colors=vertex_colors)
        return mesh
        

    def find_real_height(self, direction=None):
        def _check_polygon_in_tile(tile, points):
            tile_tf = np.eye(4)
            tile_tf[:3, 3] = tile.box[:3]
            tile_tf = np.linalg.inv(self._tileset.origin_translation) @ np.linalg.inv(self._tileset.origin_rotation)  @ tile_tf @ self._tileset.origin_rotation
            tile_center = tile_tf[:3, 3][:2]
            for point in points:
                xyz = point._tf[:3, 3]
                #  check if the point is too far from the tile center in 2D
                if np.linalg.norm(tile_center - xyz[:2]) < 80:
                    return True
            return False
            

        if direction is None:
            direction = [0, 0, 1]

        meshes_to_check = []
        for tile in self._tileset.tiles:
            if _check_polygon_in_tile(tile, self._points):
                meshes_to_check.extend(self._tileset.models[tile.uri])
        real_points = []
        for mesh in meshes_to_check:
            intersector = tm.ray.ray_pyembree.RayMeshIntersector(mesh)
            # get points and directions
            points = [point._tf[:3, 3] for point in self._points]
            directions = [direction] * len(points)
            locations, index_ray, index_tri = intersector.intersects_location(points, directions)
            for i, location in enumerate(locations):
                if location is not None:
                    real_points.append(location)
        self._points = []
        for point in real_points:
            tf = np.eye(4)
            tf[:3, 3] = point
            self._points.append(Point.from_tf(self._tileset, tf))
            print(f"Found intersection for point {point}")



            # xyz = point._tf[:3, 3]
            # #  check if point in bounds
            # if xyz[0] < bounds[0, 0] or xyz[0] > bounds[1, 0] or xyz[1] < bounds[0, 1] or xyz[1] > bounds[1, 1]:
            #     return
            # for tile in self._tileset.tiles:
            #     tile_tf = np.eye(4)
            #     tile_tf[:3, 3] = tile.box[:3]
            #     tile_tf = np.linalg.inv(self._tileset.origin_translation) @ np.linalg.inv(self._tileset.origin_rotation)  @ tile_tf @ self._tileset.origin_rotation
            #     tile_center = tile_tf[:3, 3]
            #     #  check if the point is too far from the tile center in 2D
            #     if np.linalg.norm(tile_center[:2] - xyz[:2]) > 100:
            #         continue
            #     mesh = self._tileset.models[tile.uri]
            #     for m in mesh:
            #         intersector = tm.ray.ray_pyembree.RayMeshIntersector(m)
            #         locations, index_ray, index_tri = intersector.intersects_location([xyz], [direction])
            #         if len(locations) > 0:
            #             point._tf[:3, 3] = locations[0]
            #             print(f"Found intersection for point {xyz} on tile {tile_center}")
            #             return

class Polygon:
    def __init__(self, tileset, segments):
        self._tileset = tileset
        self._segments = [PolygonSegment(tileset, segment) for segment in segments]


    def to_trimesh(self, color=None):
        meshes = []
        for segment in self._segments:
            mesh = segment.to_trimesh(color)
            if mesh is not None:
                meshes.append(mesh)
        return meshes


class MultiPolygon:
    def __init__(self, tileset, polygons):
        self._tileset = tileset
        self._polygons = [Polygon(tileset, polygon) for polygon in polygons]


    def to_trimesh(self, color=None):
        meshes = []
        for polygon in self._polygons:
            mesh = polygon.to_trimesh(color)
            if mesh is not None:
                meshes.extend(mesh)
        return meshes


class Primitive:
    def __init__(self, tileset, feature):
        self._tileset = tileset
        self._category = feature['properties']['class']
        if feature['geometry']['type'] == 'Polygon':
            primitive = Polygon(tileset, feature['geometry']['coordinates'])
        elif feature['geometry']['type'] == 'MultiPolygon':
            primitive = MultiPolygon(tileset, feature['geometry']['coordinates'])
        elif feature['geometry']['type'] == 'Point':
            primitive = Point(tileset, feature['geometry']['coordinates'])
        else:
            raise ValueError(f"Unknown geometry type: {feature['geometry']['type']}")
        self._primitive = primitive


    def to_trimesh(self, color=None):
        return self._primitive.to_trimesh(color)
    

    @property
    def category(self):
        return self._category
    

    