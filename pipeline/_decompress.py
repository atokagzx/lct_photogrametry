#!/usr/bin/env python3

from lct_solution import GLBDecompress
import json
import logging
import os
import subprocess
import concurrent.futures
from pathlib import Path
import argparse
import sys
import tqdm


class Tileset:
    def __init__(self, data_path, filename="tileset.json") -> None:
        self._logger = logging.getLogger("entrypoint.decompress.Tileset")
        self.data_path = data_path
        self.file_path = data_path + '/' + filename
        self.leaf_jsons = Tileset.get_leaf_jsons(self.file_path)
        self._logger.info(f"child tilesets to process: {len(self.leaf_jsons)}")
        self.leaf_files = Tileset.get_leaf_files(self.leaf_jsons)
        self._logger.info(f"fetched leaf tiles: {len(self.leaf_files)}")


    def get_path_from_name(name):
        parts = name.split('/')[:-1]
        return '/'.join(parts) + '/'


    def get_jsons(input_path):
        current_path = Tileset.get_path_from_name(input_path)

        with open(input_path, 'r') as file:
            data = json.load(file)

        all_jsons = []
        def process_json(data):
            if isinstance(data, str):
                if ".json" in data:
                    all_jsons.append(current_path + '/' + data)
            elif isinstance(data, list):
                return [process_json(item) for item in data]
            elif isinstance(data, dict):
                return {key: process_json(value) for key, value in data.items()}
            return data
        
        process_json(data)
        return all_jsons
    

    def get_leaf_jsons(data):
        levels = [[data]]
        while len(levels[-1]) > 0:
            new_layer = []
            for i in levels[-1]:
                new_layer += Tileset.get_jsons(i)
            levels.append(new_layer)
        return levels[-2]


    def get_leaf_files(leaf_jsons):
        models = []
        for json_path in leaf_jsons:
            def get_child(a):
                if 'content' in a and 'children' not in a:   
                    uri = Tileset.get_path_from_name(json_path) + a['content']['uri']
                    bounding_volume = a['boundingVolume']['sphere']
                    tile = [uri, bounding_volume]
                    models.append(tile)
                if 'children' in a:
                    for i in a['children']:
                        get_child(i)
            with open(json_path, 'r') as file:
                data = json.load(file)
            get_child(data['root'])
        return models


def create_glb(original_path, new_path):
    original_path = original_path
    new_path = new_path
    command = f'npx 3d-tiles-tools b3dmToGlb -i {original_path} -o {new_path}'
    return command


def b3dmToGlb(b3dm_paths, result_path):
    logger = logging.getLogger("entrypoint.decompress.b3dmToGlb")
    result_paths = []
    commands = []
    for b3dm in b3dm_paths:
        file_name = b3dm.split('/')[-1]
        new_item_path = result_path + '/' + file_name[:-4] + "glb"
        # check if file already exists
        if os.path.exists(new_item_path):
            logger.debug(f"skipping {new_item_path} as it already exists")
            result_paths.append(new_item_path)
            continue
        commands.append({
            "cmd": create_glb(b3dm, new_item_path),
            "input": b3dm,
            "output": new_item_path
        })
    num_cores = os.cpu_count() - 2
    logger.info(f"processing {len(commands)} .b3dm's using {num_cores} cores, already processed: {len(result_paths)}")
    
    def run_command(command):
        process = subprocess.Popen(command['cmd'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        process.communicate()
        if process.returncode != 0:
            logger.error(f"Failed to process {command['input']}")
            return None
        return command['output']

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_cores) as executor:
        results = list(tqdm.tqdm(executor.map(run_command, commands), total=len(commands), desc="b3dm -> glb"))
        result_paths += results
    return result_paths


def main():
    logger = logging.getLogger("entrypoint.decompress")
    argparser = argparse.ArgumentParser(description='Decompress glb files')
    argparser.add_argument('--root_dir', type=str, help='Input path', required=True)
    argparser.add_argument('--tileset', type=str, help='Tileset json file', required=True)
    argparser.add_argument('--output', type=str, help='Output path', default="output")
    output_folder = argparser.parse_args().output

    args = argparser.parse_args()

    ts = Tileset(args.root_dir, args.tileset)
    
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs('/root/.cache/compressed_glb', exist_ok=True)
    os.makedirs(output_folder + '/decompressed_glb', exist_ok=True)

    b3dm_paths = [i[0] for i in ts.leaf_files]
    logger.info(f"b3dm paths: {len(b3dm_paths)}")
    compressed_paths = b3dmToGlb(b3dm_paths, '/root/.cache/compressed_glb')
    decompressed_paths = []
    to_decompress = []
    for compressed_glb in compressed_paths:
        filename = Path(compressed_glb).name
        if os.path.exists(output_folder + '/decompressed_glb/' + filename):
            logger.debug(f"skipping {filename} as it already exists")
            decompressed_paths.append(output_folder + '/decompressed_glb/' + filename)
            continue
        to_decompress.append(compressed_glb)
    logger.info(f"decompressing {len(to_decompress)} of {len(compressed_paths)}, already done: {len(decompressed_paths)}")

    for compressed_glb in tqdm.tqdm(to_decompress, desc="Decompressing"):
        glb = GLBDecompress(Path(compressed_glb))
        glb.load_meshes()
        glb.export(Path(output_folder + '/decompressed_glb/' + compressed_glb.split('/')[-1]))
        decompressed_paths.append(output_folder + '/decompressed_glb/' + compressed_glb.split('/')[-1])
    
    logger.info(f"decompressed {len(decompressed_paths)} files")
    logger.info(f"writting planar json")
    final_json = {'data' : []}
    for i in range(len(decompressed_paths)):
        path = decompressed_paths[i][len(output_folder)+1:]
        sphere_coords = ts.leaf_files[i][1]
        box_coords = sphere_coords + [0.0, 0.0, 0.0, sphere_coords[3], 0.0, 0.0, 0.0, sphere_coords[3]]
        final_json['data'].append({
            'content' : {
                'uri' : path
            },
            "boundingVolume": {
                            "box": box_coords,
                            "sphere" : sphere_coords
                        }
        })
    with open(output_folder + '/' + 'decompressed.json', 'w') as fp:
        json.dump(final_json, fp, indent=4, ensure_ascii=False)
    logger.info(f"done")


if __name__ == '__main__':
    main()
