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
    elif sys.argv[1] == 'splitimgs':
        sys.argv.pop(1)
        from pipeline._splitimgs import main
        main()
    elif sys.argv[1] == 'tfgeojson':
        sys.argv.pop(1)
        from pipeline._transform_geojson import main
        main()
    else:
        logger.error("Available commands: decompress, splitimgs")
        sys.exit(1)
    #     main()
    # parser = argparse.ArgumentParser(description='Pipeline entrypoint')
    # parser.add_argument('--input', type=str, help='Input file')
    # parser.add_argument('--output', type=str, help='Output file')
    # args = parser.parse_args()

    # print(f'Input file: {args.input}')
    # print(f'Output file: {args.output}')

    # sys.exit(0)