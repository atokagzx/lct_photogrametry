from lct_solution.glb import GLBDecompress
import json
import os
import subprocess
import concurrent.futures
from pathlib import Path

class Tileset:
    def __init__(self, data_path, filename="tileset.json") -> None:
        self.data_path = data_path
        self.file_path = data_path + '/' + filename
        self.leaf_jsons = Tileset.get_leaf_jsons(self.file_path)
        self.leaf_files = Tileset.get_leaf_files(self.leaf_jsons)

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
    # new_path = new_path[:-4] + "glb"
    pathToLib = 'src/nodejs/'
    original_path = '../../' + original_path
    new_path = '../../' + new_path
    command = f'cd {pathToLib} && npx 3d-tiles-tools b3dmToGlb -i {original_path} -o {new_path}'
    return command

def b3dmToGlb(b3dm_paths, result_path):
    result_paths = []
    commands = []
    for b3dm in b3dm_paths:
        file_name = b3dm.split('/')[-1]
        new_item_path = result_path + '/' + file_name[:-4] + "glb"
        commands.append(create_glb(b3dm, new_item_path))
        result_paths.append(new_item_path)
    N = 20
    def run_command(command):
        process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        process.communicate()

    with concurrent.futures.ThreadPoolExecutor(max_workers=N) as executor:
        executor.map(run_command, commands)

    return result_paths

if __name__=="__main__":
    input_folder = "data/FGM_HACKATON"
    output_folder = "result"
    ts = Tileset(input_folder, 'tileset_hacaton.json')
    
    os.makedirs(output_folder, exist_ok=True)
    os.makedirs(output_folder + '/compressed_glb', exist_ok=True)
    os.makedirs(output_folder + '/decompressed_glb', exist_ok=True)

    b3dm_paths = [i[0] for i in ts.leaf_files]
    compressed_paths = b3dmToGlb(b3dm_paths, output_folder + '/compressed_glb')
    decompressed_paths = []
    for compressed_glb in compressed_paths:
        glb = GLBDecompress(Path(compressed_glb))
        glb.load_meshes()
        glb.export(Path(output_folder + '/decompressed_glb/' + compressed_glb.split('/')[-1]))
        decompressed_paths.append(output_folder + '/decompressed_glb/' + compressed_glb.split('/')[-1])

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
        json.dump(final_json, fp, indent=4)
