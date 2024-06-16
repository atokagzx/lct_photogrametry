// import * as Cesium from 'cesium';

// Your access token can be found at: https://ion.cesium.com/tokens.
// This is the default access token from your ion account

Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI0YTZhOTAwYy0wMmE2LTQwYWQtOGViZS0xMDM3MDE1ZWQzODkiLCJpZCI6MTU0MzcwLCJpYXQiOjE2ODk1NjQxMTd9.AJHX5iqrqsxONF7D70YuQc5CNYPkG5m4ltTZ4cH8QTg';

// Initialize the Cesium Viewer in the HTML element with the `cesiumContainer` ID.
const viewer = new Cesium.Viewer("cesiumContainer", {
    baseLayer: Cesium.ImageryLayer.fromProviderAsync(
        Cesium.TileMapServiceImageryProvider.fromUrl(
            Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
        )
    ),
    baseLayerPicker: false,
    geocoder: false,
});

// Add Cesium OSM Buildings, a global 3D buildings layer.
// const buildingTileset = await Cesium.createOsmBuildingsAsync();
// viewer.scene.primitives.add(buildingTileset); 

// load 3d tileset data
const tileset = viewer.scene.primitives.add(
    await Cesium.Cesium3DTileset.fromUrl("tileset_hacaton.json")
    // await Cesium.Cesium3DTileset.fromUrl("tileset_box_b3dm_new.json")
);

const customShader = new Cesium.CustomShader({
    fragmentShaderText: `
      void fragmentMain(FragmentInput fsInput, inout czm_modelMaterial material) {
        int id = fsInput.featureIds.featureId_0;
        // int id = 0;  
        vec3 color = vec3(0.0, 0.0, 0.0);
        if (id == 2) {
          color = vec3(0.0, 0.0, 1.0);
        } else if (id == 8) {
          color = vec3(0.0, 1.0, 0.0);
        }
        material.diffuse = color;
      }
    `,
});

// tileset.customShader = customShader;

// print tileset properties
// console.log(tileset);
// add button to hide and show 3d model
const button = document.createElement("button");
button.textContent = "Скрыть 3D";
button.onclick = () => {
    // tileset.customShader = tileset.customShader ? undefined : customShader;
    if (tileset.show == true) {
        button.textContent = "Показать 3D";
        tileset.show = false;
      } else {
        button.textContent = "Скрыть 3D";
        tileset.show = true;
      }
    // tileset.show = false;
}
viewer.container.appendChild(button);

viewer.zoomTo(tileset);

const classColor = {
    "park": Cesium.Color.fromBytes(0, 255, 0, 200),
    "footway": Cesium.Color.fromBytes(255, 255, 0, 200),
    "barrier": Cesium.Color.fromBytes(255, 0, 255, 200),
    "road": Cesium.Color.fromBytes(0, 0, 0, 200),
    "water": Cesium.Color.fromBytes(0, 0, 255, 200),
    "historic": Cesium.Color.fromBytes(128, 128, 128, 200),
};

// load geojson data
const dataSource = Cesium.GeoJsonDataSource.load('result.geojson');
viewer.dataSources.add(dataSource);

// set colorize function
dataSource.then(dataSource => {
    dataSource.entities.values.forEach(entity => {
        const classValue = entity.properties.class.getValue();
        entity.polygon.material = classColor[classValue];
    });
});

const parkCheckbox = document.getElementById('parkCheckbox');
const footwayCheckbox = document.getElementById('footwayCheckbox');
const barrierCheckbox = document.getElementById('barrierCheckbox');
const roadCheckbox = document.getElementById('roadCheckbox');
const waterCheckbox = document.getElementById('waterCheckbox');
const historicCheckbox = document.getElementById('historicCheckbox');
const buildingCheckbox = document.getElementById('buildingCheckbox');

function updateVisibility() {
    dataSource.then(dataSource => {
        dataSource.entities.values.forEach(entity => {
            const classValue = entity.properties.class.getValue();
            // Устанавливаем видимость в зависимости от состояния чекбоксов
            switch (classValue) {
                case 'park':
                    entity.show = parkCheckbox.checked;
                    break;
                case 'footway':
                    entity.show = footwayCheckbox.checked;
                    break;
                case 'barrier':
                    entity.show = barrierCheckbox.checked;
                    break;
                case 'road':
                    entity.show = roadCheckbox.checked;
                    break;
                case 'water':
                    entity.show = waterCheckbox.checked;
                    break;
                case 'building':
                    entity.show = buildingCheckbox.checked;
                    break;
                case 'historic':
                    entity.show = historicCheckbox.checked;
                    break;
                default:
                    // Если класс не указан, показываем объект
                    entity.show = true;
            }
        });
    });
}

parkCheckbox.addEventListener('change', updateVisibility);
footwayCheckbox.addEventListener('change', updateVisibility);
barrierCheckbox.addEventListener('change', updateVisibility);
roadCheckbox.addEventListener('change', updateVisibility);
waterCheckbox.addEventListener('change', updateVisibility);
historicCheckbox.addEventListener('change', updateVisibility);
buildingCheckbox.addEventListener('change', updateVisibility);

updateVisibility();
