import numpy as np
import trimesh as tm
from dataclasses import dataclass
import tqdm
import logging
from scipy.spatial import Delaunay
import traceback

class Point:
    def __init__(self, tileset, cartesian):
        self._logger = logging.getLogger("primitive.point")
        default_height = tileset.min_height
        self._tileset = tileset
        self._cartesian = cartesian
        self._tf = self._tileset.cartesian_to_tf([cartesian[1], cartesian[0], default_height])
        if len(cartesian) == 2:
            self._tf[:3, 3][2] = 0
        elif len(cartesian) == 3:
            self._tf[:3, 3][2] = cartesian[2]
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


class PolygonSegment:
    def __init__(self, tileset, points):
        self._logger = logging.getLogger("primitive.polygon_segment")
        self._tileset = tileset
        self._points = [Point(tileset, point) for point in points]
        # self._interpolate()
        self._find_real_height()


    def _interpolate(self):
        # interpolate points every 1 meter
        new_points = []
        for i in range(len(self._points)):
            p1 = self._points[i]
            p2 = self._points[(i + 1) % len(self._points)]
            dist = np.linalg.norm(p1._tf[:3, 3] - p2._tf[:3, 3])
            if dist < 1:
                new_points.append(p1)
                continue
            n = int(dist)
            for j in range(n):
                t = j / n
                new_point = Point.from_tf(self._tileset, p1._tf * (1 - t) + p2._tf * t)
                new_points.append(new_point)
        self._points = new_points
            

    def to_trimesh(self, color=None):
        if len(self._points) < 4:
            return None, None
        if color is None:
            color = [255, 0, 255, 80]
        points = [point._tf[:3, 3] for point in self._points]
        try:
            tri = Delaunay([point[:2] for point in points])
        except Exception as e:
            self._logger.exception(f"error triangulating polygon: {e}. Points: {points}")
            return None, None
        faces = tri.simplices
        vertex_colors = np.array([color] * len(points), dtype=np.uint8)
        mesh = tm.Trimesh(vertices=points, faces=faces, vertex_colors=vertex_colors)
        return mesh
        

    def _find_real_height(self, direction=None):
        def _check_polygon_in_tile(tile, points):
            tile_tf = np.eye(4)
            tile_tf[:3, 3] = tile.box[:3]
            tile_tf = np.linalg.inv(self._tileset.origin_translation) @ np.linalg.inv(self._tileset.origin_rotation)  @ tile_tf @ self._tileset.origin_rotation
            tile_center = tile_tf[:3, 3][:2]
            for point in points:
                xyz = point._tf[:3, 3]
                #  check if the point is too far from the tile center in 2D
                if np.linalg.norm(tile_center - xyz[:2]) < 200:
                    return True
            return False
        

        def check_if_point_is_unique(point, points):
            for p in points:
                if np.linalg.norm(p[:2] - point[:2]) < 0.5:
                    # save only the lowest point
                    if point[2] < p[2]:
                        p[2] = point[2]
                    return
            else:
                points.append(point)


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
            points_set = []
            for i, location in enumerate(locations):
                if location is not None:
                    check_if_point_is_unique(location, points_set)
            real_points.extend(points_set)


        self._points = []
        for point in real_points:
            tf = np.eye(4)
            tf[:3, 3] = point
            self._points.append(Point.from_tf(self._tileset, tf))
            self._logger.debug(f"found intersection for point {point}")


class Polygon:
    def __init__(self, tileset, segments):
        self._logger = logging.getLogger("primitive.polygon")
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
        self._logger = logging.getLogger("primitive.multi_polygon")
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
        self._logger = logging.getLogger("primitive")
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
    