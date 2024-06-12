#!/usr/bin/env python3

import json
import logging
import lct_solution as lct
import cv2


def mouse_callback(event, x, y, flags, param):
    _logger = logging.getLogger("mouse_callback")
    if event == cv2.EVENT_LBUTTONDOWN:
        tf, coords = lct.to_world_dict((x, y), param)
        _logger.info(f"Mouse click at {x}, {y}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    image_path = "out_img/rgb_0.png"
    metadata_path = "out_img/transform_0.json"
    
    image = cv2.imread(image_path)
    with open(metadata_path, "r") as f:
        metadata = json.load(f)
    cv2.namedWindow("image", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("image", mouse_callback, metadata)
    while True:
        cv2.imshow("image", image)
        key = cv2.waitKey(1)
        if key == ord("q"):
            break
    cv2.destroyAllWindows()
