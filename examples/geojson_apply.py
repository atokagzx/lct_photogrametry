#!/usr/bin/env python3

import trimesh as tm
import numpy as np
import json
import lct_solution as lct
from scipy.spatial import Delaunay

from dataclasses import dataclass


@dataclass
class Point:
    def __init__(self, tileset, cartesian, default_height = 165):
        self._tileset = tileset
        self._cartesian = cartesian
        if len(cartesian) == 2:
            self._tf = self._tileset.cartesian_to_tf([cartesian[1], cartesian[0], default_height])
        elif len(cartesian) == 3:
            self._tf = self._tileset.cartesian_to_tf([cartesian[1], cartesian[0], cartesian[2]])
        else:
            raise ValueError(f"Wrong point format: {cartesian}")


@dataclass
class PolygonSegment:
    def __init__(self, tileset, points, default_height = 165):
        self._tileset = tileset
        self._points = [Point(tileset, point, default_height) for point in points]
        

@dataclass
class Polygon:
    def __init__(self, tileset, segments):
        self._tileset = tileset
        self._segments = [PolygonSegment(tileset, segment) for segment in segments]

    
    def to_trimesh(self):
        points = []
        for segment in self._segments:
            points.extend([point._tf[:3, 3] for point in segment._points])
        tri = Delaunay([point[:2] for point in points])
        mesh = tm.Trimesh(vertices=points, faces=tri.simplices)
        mesh.fix_normals()
        return mesh


@dataclass
class MultiPolygon:
    def __init__(self, tileset, polygons):
        self._tileset = tileset
        self._polygons = [Polygon(tileset, polygon) for polygon in polygons]

    def to_trimesh(self):
        points = []
        for polygon in self._polygons:
            for segment in polygon._segments:
                points.extend([point._tf[:3, 3] for point in segment._points])
        # get only x, y in Delaunay
        # tri = Delaunay(points[:, :2])
        #     tri = Delaunay(points[:, :2])
        # TypeError: list indices must be integers or slices, not tuple
        tri = Delaunay([point[:2] for point in points])
        mesh = tm.Trimesh(vertices=points, faces=tri.simplices)
        mesh.fix_normals()
        return mesh

        


def process_geojson(geo_data, tileset):
    features = []
    for feature in geo_data['features']:
        if feature['properties']['class'] != 'park':
            continue
        if feature['geometry']['type'] == 'Polygon':
            polygon = Polygon(tileset, feature['geometry']['coordinates'])
            features.append(polygon)
        elif feature['geometry']['type'] == 'MultiPolygon':
            multipolygon = MultiPolygon(tileset, feature['geometry']['coordinates'])
            features.append(multipolygon)
        elif feature['geometry']['type'] == 'Point':
            point = Point(tileset, feature['geometry']['coordinates'])
            features.append(point)
        else:
            print(f"Unknown geometry type: {feature['geometry']['type']}")
            continue
    return features


if __name__ == "__main__":
    tileset_filename = "Tile_p3646_p720_glb/tileset_box_b3dm_crop.json"
    root_dir = "Tile_p3646_p720_glb"
    geojson_filename = "geo_classified_full.geojson"
    heght = 165
    # coords = [55.75873228450434, 37.58316666796509, 160.29468727577478]
    
    with open(geojson_filename) as f:
        geojson = json.load(f)
    

    tiles = lct.TilesLoader(tileset_filename, root_dir)

    features = process_geojson(geojson, tiles)

    meshes = tiles.models.values()
    scene = tm.Scene(meshes)
    total = 0
    bounds = [
        [-100, 400],
        [-100, 400],
        [-100, 400]
    ]
    for feature in features:
        if isinstance(feature, Polygon):
            mesh = feature.to_trimesh()
            scene.add_geometry(feature)
            total += 1
    print("total: ", total)
    # scene.add_geometry(tm.creation.axis(origin_size=1, transform=coords_tf))
    scene.add_geometry(tm.creation.axis(origin_size=5))
    scene.apply_scale(0.1)
    scene.show()
