import numpy as np
import trimesh as tm
from dataclasses import dataclass
import tqdm
import logging
from scipy.spatial import Delaunay
from ._datatypes import EmptyPolygon
import traceback
from sklearn.cluster import DBSCAN


class Point:
    def __init__(self, tileset, cartesian):
        self._logger = logging.getLogger("primitive.point")
        default_height = tileset.min_height
        self._tileset = tileset
        self._cartesian = cartesian
        self._tf = self._tileset.cartesian_to_tf([cartesian[1], cartesian[0], default_height])
        self._tf[:3, 3][2] = 0
        # if len(cartesian) == 2:
        #     self._tf[:3, 3][2] = 0
        # elif len(cartesian) == 3:
        #     self._tf[:3, 3][2] = cartesian[2]
        # else:
        #     raise ValueError(f"Wrong point format: {cartesian}")
        

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
    

    def _update_cartesian(self):
        self._cartesian = self._tileset.tf_to_cartesian(self._tf)


    def as_geojson(self):
        self._update_cartesian()
        return {
            "type": "Point",
            "coordinates": [self._cartesian[1], self._cartesian[0], self._cartesian[2]]
        }
    
def perpendicular_distance(point, line_start, line_end):
    if np.all(line_start == line_end):
        return np.linalg.norm(point - line_start)
    return np.linalg.norm(np.cross(line_end-line_start, line_start-point)) / np.linalg.norm(line_end-line_start)


class PolygonSegment:
    def __init__(self, tileset, points, apply_rdp=False):
        self._logger = logging.getLogger("primitive.polygon_segment")
        self._tileset = tileset
        self._points = [Point(tileset, point) for point in points]
        self._interpolate()
        if apply_rdp:
            origin_num = len(self._points)
            new_tfs = []
            for point in self._points:
                tf = np.eye(4)
                tf[:3, 3] = point
                new_tfs.append(tf)
            self._points = [Point.from_tf(tileset, tf) for tf in new_tfs]
            # self._logger.debug(f"Reduced points from {origin_num} to {len(self._points)}")
        self._find_real_height()
        if len(self._points) < 4:
            raise EmptyPolygon("Polygon has less than 4 points")
        
        
    @staticmethod
    def rdp(points, epsilon):
        """
        Recursively simplify points using the Ramer-Douglas-Peucker algorithm
        @param points: list of points
        @param epsilon: tolerance, maximum distance from a point to the line between the start and end points
        """
        def find_farthest_point(points, start, end):
            max_distance = 0
            index = start
            for i in range(start + 1, end):
                distance = perpendicular_distance(points[i], points[start], points[end])
                if distance > max_distance:
                    max_distance = distance
                    index = i
            return max_distance, index

        def rdp_recursive(points, start, end, epsilon):
            max_distance, index = find_farthest_point(points, start, end)
            if max_distance > epsilon:
                results1 = rdp_recursive(points, start, index, epsilon)
                results2 = rdp_recursive(points, index, end, epsilon)
                return results1[:-1] + results2
            else:
                return [points[start], points[end]]

        return rdp_recursive(points, 0, len(points) - 1, epsilon)



    def _interpolate(self, step=1):
        new_points = []
        for i in range(len(self._points)):
            p1 = self._points[i]
            p2 = self._points[(i + 1) % len(self._points)]
            dist = np.linalg.norm(p1._tf[:3, 3] - p2._tf[:3, 3])
            if dist < step:
                new_points.append(p1)
                continue
            n = int(dist / step)
            for j in range(n):
                t = j / n
                new_point = Point.from_tf(self._tileset, p1._tf * (1 - t) + p2._tf * t)
                new_points.append(new_point)
            

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
                if np.linalg.norm(tile_center - xyz[:2]) < 1.2 * tile.box[3]:
                    return True
            return False
        

        def check_if_point_is_unique(point, points):
            for p in points:
                if np.linalg.norm(p[:2] - point[:2]) < 0.001:
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

        if len(real_points) < 5:
            self._points = []
            return
        new_points = []
        # # apply db scan to filter out outliers
        # real_points = np.array(real_points)
        # # eps = 3 meters, min_samples = 3
        # db = DBSCAN(eps=3, min_samples=3).fit(real_points)
        # labels = db.labels_
        # unique_labels = set(labels)
        # #  find the most common label
        # max_label = None
        # max_count = 0
        # for label in unique_labels:
        #     count = np.sum(labels == label)
        #     if count > max_count:
        #         max_count = count
        #         max_label = label
        # apply dbscan only for z axis
        real_points = np.array(real_points)
        labels = np.zeros(len(real_points))
        db = DBSCAN(eps=3, min_samples=4).fit(real_points[:, 2].reshape(-1, 1))
        labels = db.labels_
        unique_labels = np.unique(labels)
        if len(unique_labels) == 0:
            print("No labels")
        labels_count = np.zeros(len(unique_labels))
        for i, label in enumerate(unique_labels):
            labels_count[i] = np.sum(labels == label)
        # max_label = unique_labels[np.argmax(labels_count)]
        max_label = np.argmax(labels_count)
        # compute mean height only for the most common label
        if max_label == -1:
            print("No labels")
            self._points = []
            return
        mean_height = np.mean(real_points[labels == max_label][:, 2])
        for point in self._points:
            nearst_idx = np.argmin([np.linalg.norm(x[:2] - point._tf[:3, 3][:2]) for x in real_points])
            if np.linalg.norm(point._tf[:3, 3][:2] - real_points[nearst_idx][:2]) < 0.5:
                tf = np.eye(4)
                tf[:3, 3] = real_points[nearst_idx]
                if labels[nearst_idx] != max_label:
                    tf[:3, 3][2] = mean_height
                new_points.append(Point.from_tf(self._tileset, tf))
            else:
                # height mean of real points
                tf = np.eye(4)
                tf[:3, 3] = point._tf[:3, 3]
                tf[:3, 3][2] = mean_height
                new_points.append(Point.from_tf(self._tileset, tf))
        self._points = new_points


    def as_geojson(self):
        return [point.as_geojson()['coordinates'] for point in self._points]


class Polygon:
    def __init__(self, tileset, segments):
        self._logger = logging.getLogger("primitive.polygon")
        self._tileset = tileset
        self._segments = []
        for segment in segments:
            try:
                polygon_segment = PolygonSegment(tileset, segment)
            except EmptyPolygon as e:
                continue
            self._segments.append(polygon_segment)
        if not self._segments:
            raise EmptyPolygon("Polygon has no segments")
        

    def to_trimesh(self, color=None):
        meshes = []
        for segment in self._segments:
            mesh = segment.to_trimesh(color)
            if mesh is not None:
                meshes.append(mesh)
        return meshes
    

    def as_geojson(self):
        data = {
            "type": "Polygon",
            "coordinates": []
        }
        for segment in self._segments:
            data['coordinates'].append(segment.as_geojson())
        return data
        


class MultiPolygon:
    def __init__(self, tileset, polygons):
        self._logger = logging.getLogger("primitive.multi_polygon")
        self._tileset = tileset
        # self._polygons = [Polygon(tileset, polygon) for polygon in polygons]
        self._polygons = []
        for polygon in polygons:
            try:
                polygon = Polygon(tileset, polygon)
            except EmptyPolygon as e:
                continue
            self._polygons.append(polygon)
        if not self._polygons:
            raise EmptyPolygon("MultiPolygon has no polygons")


    def to_trimesh(self, color=None):
        meshes = []
        for polygon in self._polygons:
            mesh = polygon.to_trimesh(color)
            if mesh is not None:
                meshes.extend(mesh)
        return meshes
    

    def as_geojson(self):
        data = {
            "type": "MultiPolygon",
            "coordinates": []
        }
        for polygon in self._polygons:
            data['coordinates'].append(polygon.as_geojson())
        return data


class Primitive:
    def __init__(self, tileset, feature):
        self._logger = logging.getLogger("primitive")
        self._tileset = tileset
        self._properties = feature['properties']
        self._category = feature['properties']['class']
        try:
            if feature['geometry']['type'] == 'Polygon':
                primitive = Polygon(tileset, feature['geometry']['coordinates'])
            elif feature['geometry']['type'] == 'MultiPolygon':
                primitive = MultiPolygon(tileset, feature['geometry']['coordinates'])
            elif feature['geometry']['type'] == 'Point':
                primitive = Point(tileset, feature['geometry']['coordinates'])
            else:
                raise ValueError(f"Unknown geometry type: {feature['geometry']['type']}")
        except EmptyPolygon as e:
            raise
        self._primitive = primitive


    def to_trimesh(self, color=None):
        return self._primitive.to_trimesh(color)
    

    @property
    def category(self):
        return self._category
    

    def as_geojson(self):
        data = {
            "type": "Feature",
            "properties": self._properties
        }
        data['geometry'] = self._primitive.as_geojson()
        return data
    