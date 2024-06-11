
import math
import numpy as np


def wsg84_to_cartesian(x, y, z):
    '''
    Convert WSG-84 coordinates to cartesian
    '''
    # WGS-84
    a = 6378137.0 # Радиус Земли
    e = 8.1819190842622e-2 # Эксцентриситет

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


def to_world(point, tf, img_size, camera_step):
    '''
    Convert image point to world coordinates
    @param point: tuple of two integers, image point
    @param tf: 4x4 numpy array, transformation matrix
    @param img_size: int, image size
    @param camera_step: float, step of the camera (meters)
    @return: tuple of 4x4 numpy array and tuple of three floats representing world coordinates
    '''
    x_meter = -(img_size / 2 - point[0]) * camera_step / img_size
    y_meter = (img_size / 2 - point[1]) * camera_step / img_size
    z_meter = 0
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
    return to_world(point, tf, img_size, camera_step)