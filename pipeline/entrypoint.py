#!/usr/bin/env python3

import sys
import argparse
import logging


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("entrypoint")
    if len(sys.argv) < 2:
        logger.error("Usage: pipeline.sh [command]")
        sys.exit(1)
    if sys.argv[1] == 'decompress':
        sys.argv.pop(1)
        from pipeline._decompress import main
        main()
    if sys.argv[1] == 'create_geojson':
        sys.argv.pop(1)
        from pipeline._classify_tiles import main
        main()
    elif sys.argv[1] == 'rasterize':
        sys.argv.pop(1)
        from pipeline._rasterize import main
        main()
    elif sys.argv[1] == 'tfgeojson':
        sys.argv.pop(1)
        from pipeline._transform_geojson import main
        main()
    else:
        logger.error("Available commands: decompress, create_geojson, rasterize, tfgeojson")
        sys.exit(1)