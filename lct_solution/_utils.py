import numpy as np
import open3d as o3d
import trimesh as tm
import typing
from ._datatypes import Tile


def validate_rotation_matrix(R):
    """
    Check if a matrix is a valid rotation matrix.
    """
    is_orthogonal = np.allclose(np.dot(R, R.T), np.eye(3))
    is_det_one = np.isclose(np.linalg.det(R), 1)
    return is_orthogonal and is_det_one


def find_rotation_matrix(plane_eq):
    '''
    Compute the rotation matrix for a plane given by its equation Ax + By + Cz + D = 0
    @param plane_eq: tuple of 4 floats (A, B, C, D)
    @return: 3x3 numpy array
    '''
    A, B, C, _D = plane_eq
    norm = np.sqrt(A**2 + B**2 + C**2)
    A /= norm
    B /= norm
    C /= norm
    N = np.array([A, B, C])
    Z = np.array([0, 0, 1])
    V = np.cross(N, Z)
    V /= np.linalg.norm(V)
    U = np.cross(V, N)
    R = np.column_stack((N, U, V))
    assert validate_rotation_matrix(R)
    return R


def compute_origin(tiles: typing.List[Tile]) -> np.ndarray:
    cluster = o3d.geometry.PointCloud()
    for tile in tiles:
        point = o3d.geometry.PointCloud()
        point_points = np.array(tile.box[:3]).reshape(1, 3)
        point.points = o3d.utility.Vector3dVector(point_points)
        cluster += point
    plane_model, inliers = cluster.segment_plane(distance_threshold=0.1, ransac_n=3, num_iterations=1000)
    R = find_rotation_matrix(plane_model)
    rot_matrix = np.eye(4)
    rot_matrix[:3, :3] = R
    #  rotate by -90 degrees around y axis
    add_rot = np.array([[0, 0, 1, 0],
                        [0, 1, 0, 0],
                        [-1, 0, 0, 0],
                        [0, 0, 0, 1]])
    rot_matrix = np.dot(rot_matrix, add_rot)
    return rot_matrix