
import math
import numpy as np


a = 6378137.0 # Радиус Земли
e = 8.1819190842622e-2 # Эксцентриситет


def wsg84_to_cartesian(x, y, z):
    '''
    Convert WSG-84 coordinates to cartesian
    '''
    b = math.sqrt(a**2 * (1-e**2))
    ep = math.sqrt((a**2 - b**2) / b**2)
    p = math.sqrt(x**2 + y**2)
    th = math.atan2(a*z, b*p)
    lon = math.atan2(y, x)
    lat = math.atan2((z + ep**2 * b * math.sin(th)**3), (p - e**2 * a * math.cos(th)**3))
    n = a / math.sqrt(1 - e**2 * math.sin(lat)**2)
    alt = p / math.cos(lat) - n

    lat = lat * (180.0/math.pi)
    lon = lon * (180.0/math.pi)
    return lat, lon, alt


def cartesian_to_wsg84(lat, lon, alt):
    '''
    Convert cartesian coordinates to WSG-84
    '''    
    lat = lat * (math.pi/180.0)
    lon = lon * (math.pi/180.0)
    n = a / math.sqrt(1 - e**2 * math.sin(lat)**2)
    x = (n + alt) * math.cos(lat) * math.cos(lon)
    y = (n + alt) * math.cos(lat) * math.sin(lon)
    z = (n * (1 - e**2) + alt) * math.sin(lat)
    return x, y, z


def to_world(point, tf, img_size, camera_step, camera_dst):
    '''
    Convert image point to world coordinates
    @param point: tuple of two integers, image point
    @param tf: 4x4 numpy array, transformation matrix
    @param img_size: int, image size
    @param camera_step: float, step of the camera (meters)
    @param camera_dst: float, distance from the camera to the origin
    @return: tuple of 4x4 numpy array and tuple of three floats representing world coordinates
    '''
    x_meter = -(img_size / 2 - point[0]) * camera_step / img_size
    y_meter = (img_size / 2 - point[1]) * camera_step / img_size
    z_meter = 0
    z_meter = -camera_dst
    point_tf = np.eye(4)
    point_tf[:3, 3] = [x_meter, y_meter, z_meter]
    point_tf = np.dot(tf, point_tf)
    coords = wsg84_to_cartesian(point_tf[0, 3], point_tf[1, 3], point_tf[2, 3])
    return point_tf, coords


def to_world_dict(point, metadata_dict):
    '''
    Convert image point to world coordinates
    @param point: tuple of two integers, image point
    @param metadata_dict: dict, metadata dictionary
    @return: tuple of 4x4 numpy array and tuple of three floats representing world coordinates
    '''
    tf = np.array(metadata_dict["tf"])
    img_size = metadata_dict["image_size"]
    camera_step = metadata_dict["step_m"]
    camera_dst = metadata_dict["camera_dst"]
    return to_world(point, tf, img_size, camera_step, camera_dst)
