import numpy as np
import trimesh as tm
from dataclasses import dataclass
from scipy.spatial import Delaunay


class Point:
    def __init__(self, tileset, cartesian, default_height = 168):
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
    

class PolygonSegment:
    def __init__(self, tileset, points):
        self._tileset = tileset
        self._points = [Point(tileset, point) for point in points]

    def to_trimesh(self, color=None):
        if color is None:
            color = [255, 0, 255, 80]
        points = [point._tf[:3, 3] for point in self._points]
        # check if any point is outside of the bounds
        for point in points:
            if point[0] < -500 or point[0] > 500 or point[1] < -500 or point[1] > 500:
                return None, None
        tri = Delaunay([point[:2] for point in points])
        faces = tri.simplices
        vertex_colors = np.array([color] * len(points), dtype=np.uint8)
        mesh = tm.Trimesh(vertices=points, faces=faces, vertex_colors=vertex_colors)
        return mesh
        

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
    