import osmnx as ox
import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon, LineString, Point, box
import math
from shapely.affinity import scale
import elevation
import rasterio
from rasterio.mask import mask
import srtm


# Define the bounding box coordinates (north, south, east, west)
# patriki
'''
north = 55.7705
south = 55.7552
east = 37.5826
west = 37.6083
'''

#zaryadye
'''
north = 55.75298
south = 55.74915
east = 37.62324
west = 37.63376
'''

# Download the polygon data for the specified bounding box
tags = {
    'building': True,
    'highway': ['residential', 'primary', 'secondary', 'tertiary', 'footway', 'motorway', 'trunk', 'unclassified', 'service', 'steps'],
    'leisure': 'park',
    'landuse': ['park', 'grass'],
    'height': True,
    'building:levels': True,
    'lanes': True,
    'width': True,
    'historic': True,
    'natural': ['water', 'riverbank', 'tree'],
    'amenity': ['bench', 'fountain'],
    'barrier': ["bollard", "fence", "hedge", "wall"],
    'man_made': 'pole',
    'layer': True
}

# Use SRTM.py to get elevation data
elevation_data = srtm.get_data()

def classify(row):
    if pd.notnull(row["historic"]):
        return 'historic'
    elif row["highway"] in ['primary', 'secondary', 'tertiary', "motorway", "trunk", "residential", 'unclassified', "service"]:
        return "road"
    elif row["highway"] in ["footway", "steps"]:
        return "footway"
    elif row["landuse"] in ["park", 'grass'] or row["leisure"] == "park":
        return "park"
    elif row['natural'] in ['water', 'riverbank']:
        return 'water'
    elif row['natural'] == 'tree' or row["amenity"] in ['bench', 'fountain'] or row['barrier'] in ["fence"] or row['man_made'] == 'pole':
        return 'barrier'
    elif pd.notnull(row["building"]):
        return "building"


def extract_width(row):
    if not pd.isna(row["highway"]) and not pd.isna(row["width"]):
        return float(row["width"])
    elif not pd.isna(row['highway']) and not pd.isna(row['lanes']):  # Check if it's a road with lanes and width
        return int(row['lanes']) * 3  # Assuming lanes and width define the road's height
    else:
        return 3

# Get elevation for a point
def get_elevation(point):
    if isinstance(point, Point):
        return elevation_data.get_elevation(point.y, point.x, approximate=True)+ 12
    else:

        return 0

def linestring_to_polygon(linestring, width):
    if isinstance(linestring, LineString):
        if linestring.is_empty or len(linestring.coords) < 2:
            return None
        else:
            polygon = linestring.buffer(width/2,quad_segs=1)
            return polygon
    else:
        return linestring


# Convert points to small circular polygons
def point_to_square(point, size=1):
    if isinstance(point, Point):
        half_size = size / 2
        square_coords = [
            (point.x - half_size, point.y - half_size),
            (point.x + half_size, point.y - half_size),
            (point.x + half_size, point.y + half_size),
            (point.x - half_size, point.y + half_size),
            (point.x - half_size, point.y - half_size)
        ]
        return Polygon(square_coords)
    else:
        return point


# Convert height or building:levels to a numeric height in meters
def extract_height(row):
    scaler = 1
    if pd.notnull(row['height']):
        return float(''.join(i for i in row['height'].split('.')[0] if i.isdigit())) / scaler
    elif pd.notnull(row['building:levels']):
        return float(row['building:levels']) * 3 / scaler # Assuming each level is approximately 3 meters
    elif row['natural'] == 'tree' or row['barrier'] in ["fence"] or row['man_made'] == 'pole':
        return 3 / scaler
    elif row["amenity"] in ['bench', 'fountain']:
        return 0.5 / scaler
    else:
        return 0



def polygon_to_3d(polygon, height):
    if isinstance(polygon, Polygon):
        # Create a bounding box for the building polygon
        minx, miny, maxx, maxy = polygon.bounds
        building_box = box(minx, miny, maxx, maxy)
        # Get elevation of the centroid of the building
        centroid = building_box.centroid
        base_height = get_elevation(centroid)
        exterior_coords_3d = [(x, y, get_elevation(Point(x, y)) + height if height is not None else get_elevation(Point(x, y))) for x, y in polygon.exterior.coords]
        interiors_coords_3d = [
            [(x, y, get_elevation(Point(x, y)) + height if height is not None else get_elevation(Point(x, y))) for x, y in interior.coords]
            for interior in polygon.interiors
        ]
        return Polygon(exterior_coords_3d, interiors_coords_3d)
    elif isinstance(polygon, MultiPolygon):
        return MultiPolygon([polygon_to_3d(poly, height) for poly in polygon.geoms])
    else:
        return polygon


import re
import math

def get_lat_lon(coords):
    x,y,z = coords
    a = 6378137.0 # Радиус Земли
    e = 8.1819190842622e-2 # Эксцентриситет

    # Вычисления
    b = math.sqrt(a**2 * (1-e**2))
    ep = math.sqrt((a**2 - b**2) / b**2)
    p = math.sqrt(x**2 + y**2)
    th = math.atan2(a*z, b*p)
    lon = math.atan2(y, x)
    lat = math.atan2((z + ep**2 * b * math.sin(th)**3), (p - e**2 * a * math.cos(th)**3))
    n = a / math.sqrt(1 - e**2 * math.sin(lat)**2)
    alt = p / math.cos(lat) - n

    # Конвертация в градусы
    lat = lat * (180.0/math.pi)
    lon = lon * (180.0/math.pi)
    return lat, lon


def b3dm_get_coords(path):
    with open(path, "rb") as f:
        s = f.read()
        center = list(map(float, re.findall(b'"RTC_CENTER":\[([0-9\.\,\-]+)\]', s)[0].decode('ascii').split(",")))
        min = list(map(float, re.findall(b'"min":\[([0-9\.\,\-]+)\]', s)[0].decode('ascii').split(",")))
        max = list(map(float, re.findall(b'"max":\[([0-9\.\,\-]+)\]', s)[0].decode('ascii').split(",")))
        left_corner = [center[0] + min[0], center[1] + min[1], center[2] + min[2]]
        right_corner = [center[0] + max[0], center[1] + max[1], center[2] + max[2]]
        print(left_corner, right_corner)
        return get_lat_lon(left_corner), get_lat_lon(right_corner)


def tileset_get_coords(path):
    import json

    with open(path) as f:
        d = json.load(f)
        childrens = d['root']["children"]
    min_lat = 1e10
    min_lon = 1e10
    ecef_min_lat = None
    ecef_max_lat = None
    ecef_min_lon = None
    ecef_max_lon = None
    err_cnst_rad = 0.0011
    max_lat = 0
    max_lon = 0
    min_z = 0
    max_z = 0
    for child in childrens:
        child = child['boundingVolume']['sphere']
        lat, lon = get_lat_lon(child[:3])
        if (lat < min_lat):
            min_lat = lat
            ecef_min_lat = child
        if (lon < min_lon):
            min_lon = lon
            ecef_min_lon = child
        if (lat > max_lat):
            max_lat = lat
            ecef_max_lat = child
        if (lon > max_lon):
            max_lon = lon
            ecef_max_lon = child

    return (min_lat - err_cnst_rad, min_lon - err_cnst_rad), (max_lat + err_cnst_rad, max_lon + err_cnst_rad)


import pickle


def process(left_corner, right_corner, output_file = "bounding_box_features_3d.geojson", load_from_local=None):
    south, west = left_corner
    north, east = right_corner
    if load_from_local is not None:
        # Clip the data to the bounding box
        with open(load_from_local, 'rb') as handle:
            gdf = pickle.load(handle)
        bbox = box(west, south, east, north)
        gdf = gdf[gdf.intersects(bbox)]
    else:
        gdf = ox.geometries.geometries_from_bbox(north, south, east, west, tags=tags)

    if 'height' not in gdf:
        gdf["height"] = None
    if 'man_pole' not in gdf:
        gdf["man_made"] = None
    if 'building' not in gdf:
        gdf["building"] = None
    if 'highway'  not in gdf:
        gdf["highway"] = None      
    if 'leisure' not in gdf:
        gdf["leisure"] = None
    if 'landuse' not in gdf:
        gdf["landuse"] = None
    if 'height' not in gdf:
        gdf["height"] = None
    if 'building:levels' not in gdf:
        gdf["building:levels"] = None
    if 'lanes' not in gdf:
        gdf["lanes"] = None
    if 'width' not in gdf:
        gdf["width"] = None
    if 'historic' not in gdf:
        gdf["historic"] = None
    if 'natural' not in gdf:
        gdf["natural"] = None
    if 'amenity' not in gdf:
        gdf["amenity"] = None
    if 'barrier' not in gdf:
        gdf["barrier"] = None
    if 'layer' not in gdf:
        gdf["layer"] = None
    
    gdf['width'] = gdf.apply(extract_width, axis=1)

    original_crs = gdf.crs
    gdf = gdf.to_crs('+proj=utm +zone=10 +ellps=GRS80 +datum=NAD83 +units=m +no_defs')
    gdf['geometry'] = gdf.apply(lambda row: linestring_to_polygon(row['geometry'], row['width']) if row['geometry'].type == 'LineString' else row['geometry'], axis=1)
    gdf['geometry'] = gdf.apply(lambda row: point_to_square(row['geometry']) if row['geometry'].type == 'Point' else row['geometry'], axis=1)
    gdf = gdf.to_crs(original_crs)

    # Ensure only polygons are included and filter by type
    gdf = gdf[(gdf.geometry.type == 'Polygon') | (gdf.geometry.type == 'MultiPolygon') | (gdf.geometry.type == 'LineString') | (gdf.geometry.type == 'Point')]

    gdf['height'] = gdf.apply(extract_height, axis=1)

    gdf['geometry'] = gdf.apply(lambda row: polygon_to_3d(row['geometry'], row['height']), axis=1)

    gdf['class'] = gdf.apply(classify, axis=1)

    # Save the GeoDataFrame to a GeoJSON file
    gdf = gdf.dropna(subset="class")
    gdf[["geometry", "name", "class", "layer"]].to_file(output_file, driver='GeoJSON')

    print(f"3D GeoJSON file saved as {output_file}")

"""
left_corner, right_corner = tileset_get_coords("/content/tileset_hacaton.json")
process(left_corner, right_corner)
"""

import logging
import argparse
from pathlib import Path

def main():
    logger = logging.getLogger("entrypoint.create_geojson")
    argparser = argparse.ArgumentParser(description='Create initial geojson')
    argparser.add_argument('--tileset_json', type=str, help='Tileset json file')
    argparser.add_argument('--tileset_b3dm', type=str, help='Tileset b3dm file')
    argparser.add_argument('--output', type=str, help='Output path', default="output/initial.geojson")

    args = argparser.parse_args()
    output_filename = Path(args.output)
    input_json_filename = args.tileset_json
    input_b3dm_filename = args.tileset_b3dm

    if (input_json_filename is None and input_b3dm_filename is None):
        logger.fatal("No input data")
        exit(1)
    

    if input_json_filename is not None:
        logger.info("Getting coordinates from tileset...")
        left_corner, right_corner = tileset_get_coords(input_json_filename)

    if input_b3dm_filename is not None:
        logger.info("Getting coordinates from b3dm...")
        left_corner, right_corner = b3dm_get_coords(input_b3dm_filename)

    logger.info("Creating geojson...")
    process(left_corner, right_corner, output_file=output_filename)
    logger.info("Geojson successfully created!")
