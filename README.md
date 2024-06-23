# principal point misis

Решение команды principal point misis для хакатона Лидеры Цифровой Трансформации 2024.
Задача №6: Сервис для автоматического моделирования движения на Цифровом двойнике Москвы 

## Установка

Убедитесь, что у вас установлен докер, и запустите скрипт.

```bash
./docker/build.sh
```

Либо загрузите собранный образ.

## Использование

Для того, чтобы получить GeoJson, необходимо запустить следующий набор команд. При необходимости замените параметры на пути к вашим входным данным.

```bash
# Шаг 1: Предобработка входных 3д моделей
# root_dir: путь к тайлсету
# tileset: путь к файлу .json
./docker/pipeline.sh decompress --root_dir FGM_HACKATON --tileset tileset_hacaton.json

# Шаг 2: Получение 2D geojson
# tileset_json: путь к тайлсету, представленному в виде .json
# output: имя выходного файла (с расширением .geojson)
./docker/pipeline.sh create_geojson --tileset_json ./FGM_HACKATON/tileset_hacaton.json --output ./FGM_HACKATON/result.geojson

# Шаг 3: Получение 3D geojson согласно входной 3D модели
# root_dir: путь к распакованному тайлсету
# planar: путь к файлу .json из распакованного тайлсета
# input: путь к 2D .geojson
./docker/pipeline.sh tfgeojson --root_dir output/decompressed --planar decompressed.json --input ./FGM_HACKATON/result.geojson
# результат находится в по пути output/transformed.geojson

# Шаг 4: Растеризация 3D tileset
# root_dir: путь к распакованному тайлсету
# planar: путь к файлу .json из распакованного тайлсета
./docker/pipeline.sh rasterize --root_dir output/decompressed --planar decompressed.json

# Шаг 5 (опционально): Визуализация результата
./docker/cesium_web.sh 

# Шаг 6 (опционально): Запуск в плагине Unreal Engine
# инструкция и плагин находятся в папке внутри yandex disk
```

## Модули, используемые в пайплайне
#### Преобразование исходного датасета
- Входные данные: 3D модель в формате `tileset.json` или `.b3dm`
- Выходные данные: Тот же датасет в формате `decompressed glb`

Для дальнейшей обработки входных данных и получения текстур и полигонов из 3D тайлсетов, мы преобразуем входные `b3dm` согласно структуре, указанной в `.json`, сначала в файлы `.glb` с компрессией `draco`, а затем распаковываем их в несжатые `.glb`, которые уже возможно обрабатывать при помощи стандартных библиотек. Мы также получаем новый `decompressed.json`, учитывающий новую структуру файлов, но сохраняющий данные о координатах.

#### Генерация 2D geojson
- Входные данные: локальная копия разметки или доступ к OpenStreetMap
- Выходные данные: файл `.geojson` с двумерной разметкой

Чтобы произвести корректную и качественную сегментацию, мы используем данные из OpenStreetMap - некоммерческий opensource веб-картографический проект.
С помощью него мы получаем координаты зданий, дорог и нужных нам объектов. Далее полученные объекты мы преобразуем в полигоны. Для правильной отрисовки дорог мы используем метаданные об их ширине и количестве полос, также для всех объектов используется информация о высоте.
###### Загрузка карты со всеми объектами
Сначала достаются координаты 3D модели из tileset.json файла или отдельного b3dm (указывается флагами), далее мы указываем теги с объектами, которые мы хотим достать. После этого идет подгрузка карты по полученным координатам из интернета (или из локального файла, указав путь load_from_local в функции process).
###### Маппинг высот и ширины 
Воспользовавшись информацией из метаданных мы даем каждому полигону свою высоту и ширину.
Также чтобы корректно отображать полигоны вместе с моделями используется информация о высоте точек над уровнем моря полученная из SRTM.
###### Классификация объектов
Получив информацию об объектах мы можем классифицировать их по категориям, к примеру деревья, скамейки, заборы в barriers, а тропы, тротуары в footway.
###### Сохранение полигонов
Все классифицированные полигоны и мультиполигоны с указанием их названий, класса и высоты мы сохраняем в формате GeoJSON.

#### Получение 3D geojson согласно входной 3D модели
- Входные данные: 2D geojson, множество полигонов с геопривязкой
- Выходные данные: geojson, адаптированный к исходной 3D модели

###### Выравнивание уровня горизонта относительно мира
Для поиска угла отклонения набора мешей относительно мира мы ииспользовали метод **RANSAC** (Random Sample Consensus). Этот метод позволяет нам найти наиболее вероятное положение мешей относительно мира, учитывая возможные выбросы.
###### Примение проекции на плоскость
Для применения проекции на плоскость мы использовали метод **Ray Casting**. Этот метод позволяет нам найти точки пересечения лучей, исходящих из камеры, с мешем. После этого мы можем найти координаты точек пересечения на плоскости.
###### Фильтрация полученных данных 
Для фильтрации кластеров точек мы использовали метод **DBSCAN** (Density-Based Spatial Clustering of Applications with Noise). Этот метод позволяет нам найти кластеры точек, учитывая их плотность. Таким образом, мы можем отфильтровать выбросы и найти наиболее плотные кластеры точек.

##### Растеризация 3D tileset
В результате выполнения команды `rasterize` в папке `output/decompressed` появится папка `rasterized`, в которой будут находиться растеризованные изображения, полученные с помощью ортогональной проекции. В качестве добавочной информации создается файл `.json`, в котором содержится информация, позволяющая произвести обратное преобразование изображения в координаты на 3D модели *(pixel -> world coordinates)*.
![Пример растеризованых изображений](/media/rasterized.png)

#### Визуализация полученных данных

Мы используем модифицированную Cesium Web для отображения результата с учётом классов и возможности отображать только выбранные объекты на 3D модели. Также для отладки доступна визуализцаия инструментами *Trimesh* и *Open3D*. Примеры использования можно найти в директории [**examples**](/examples).
![Пример визуализации](/media/view_model_screenshot.png)

#### Ручное редактирование полученного geojson
https://github.com/rowanwins/geojson-editor

#### Плагин для Unreal Engine
Документация находится внутри Yandex Disk

## Архитектура
- pre-built Docker image для отсутствия необходимости установки зависимостей и запуска без доступа к интернету
- модульная архитектура с сервисами, выполняющими отдельные задачи внутри пайплайна
- мультипроцессинг в отдельных вычислительно сложных задачах