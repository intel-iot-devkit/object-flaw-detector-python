"""Object flaw detector."""
'''
* Copyright (c) 2018 Intel Corporation.
*
* Permission is hereby granted, free of charge, to any person obtaining
* a copy of this software and associated documentation files (the
* "Software"), to deal in the Software without restriction, including
* without limitation the rights to use, copy, modify, merge, publish,
* distribute, sublicense, and/or sell copies of the Software, and to
* permit persons to whom the Software is furnished to do so, subject to
* the following conditions:
*
* The above copyright notice and this permission notice shall be
* included in all copies or substantial portions of the Software.
*
* THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
* EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
* MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
* NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
* LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
* OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
* WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*
'''

import socket
import math
import sys
import cv2
import os

from argparse import ArgumentParser
from influxdb import InfluxDBClient
from math import atan2

import numpy as np

OBJECT_AREA_MIN = 9000
OBJECT_AREA_MAX = 50000
LOW_H = 0
LOW_S = 0
LOW_V = 47
# Thresholding of an Image in a color range
HIGH_H = 179
HIGH_S = 255
HIGH_V = 255
# Lower and upper value of color Range of the object
# for color thresholding to detect the object
LOWER_COLOR_RANGE = (0, 0, 0)
UPPER_COLOR_RANGE = (174, 73, 255)
COUNT_OBJECT = 0
HEIGHT_OF_OBJ = 0
WIDTH_OF_OBJ = 0

OBJECT_COUNT = "Object Number : {}".format(COUNT_OBJECT)


def build_argparser():
    """
    Parse the command line arguments.

    :return: command line arguments
    """
    parser = ArgumentParser()
    parser.add_argument('-dir', '--directory',
                        required=False,
                        help="Name of the directory to "
                        "which defective images are saved")
    parser.add_argument('-i', '--input',
                        required=True,
                        help="Required. Path to the video file. "
                        "'CAM' for capturing video stream from camera.")
    parser.add_argument("-d", "--distance",
                        required=False,
                        type=float,
                        default=None,
                        help="Distance between camera "
                        "and object in millimeters")
    parser.add_argument("-f", "--fieldofview",
                        required=False,
                        type=float,
                        default=None,
                        help="Field of view of camera")

    return parser


def dimensions(box):
    """
    Return the length and width of the object.

    :param box: consists of top left, right and bottom left, right co-ordinates
    :return: Length and width of the object
    """
    (tl, tr, br, bl) = box
    x = int(math.sqrt(math.pow((bl[0] - tl[0]), 2) + math.pow((bl[1] - tl[1]), 2)))
    y = int(math.sqrt(math.pow((tl[0] - tr[0]), 2) + math.pow((tl[1] - tr[1]), 2)))

    if x > y:
        return x, y
    else:
        return y, x


def get_ip_address():
    """
    Return IP address of the server.

    :return: None
    """
    hostname = socket.gethostname()
    ipaddress = socket.gethostbyname(hostname)
    port = 8086
    proxy = {"http": "http://{}:{}".format(ipaddress, port)}
    return ipaddress, port, proxy


def get_orientation(contours):
    """
    Gives the angle of the orientation of the object in radians.
    Step 1: Convert 3D matrix of contours to 2D.
    Step 2: Apply PCA algorithm to find angle of the data points.
    Step 3: If angle is greater than 0.5, return_flag is made to True
            else false.
    Step 4: Save the image in "Orientation" folder if it has a
            orientation defect.

    :param contours: contour of the object from the frame
    :return: angle of orientation of the object in radians
    """
    size_points = len(contours)
    # data_pts stores contour values in 2D
    data_pts = np.empty((size_points, 2), dtype=np.float64)
    for i in range(data_pts.shape[0]):
        data_pts[i, 0] = contours[i, 0, 0]
        data_pts[i, 1] = contours[i, 0, 1]
    # Use PCA algorithm to find angle of the data points
    mean, eigenvector = cv2.PCACompute(data_pts, mean=None)
    angle = atan2(eigenvector[0, 1], eigenvector[0, 0])
    return angle


def detect_orientation(frame, contours):
    """
    Identifies the Orientation of the object based on the detected angle.

    :param frame: Input frame from video
    :param contours: contour of the object from the frame
    :return: defect_flag, defect
    """
    defect = "Orientation"
    global OBJECT_COUNT
    # Find the orientation of each contour
    angle = get_orientation(contours)
    # If angle is less than 0.5 then no orientation defect is present
    if angle < 0.5:
        defect_flag = False
    else:
        x, y, w, h = cv2.boundingRect(contours)
        print("Orientation defect detected in object {}".format(COUNT_OBJECT))
        defect_flag = True
        cv2.imwrite("{}/orientation/Orientation_{}.png"
                    .format(base_dir, COUNT_OBJECT),
                    frame[y: y + h , x : x + w])
        cv2.putText(frame, OBJECT_COUNT, (5, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Defect: {}".format(defect), (5, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Length (mm): {}".format(HEIGHT_OF_OBJ), (5, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Width (mm): {}".format(WIDTH_OF_OBJ), (5, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.imshow("Out", frame)
        cv2.waitKey(2000)
    return defect_flag, defect


def detect_color(frame, cnt):
    """
    Identifies the color defect W.R.T the set default color of the object.
    Step 1: Increase the brightness of the image.
    Step 2: Convert the image to HSV Format. HSV color space gives more
            information about the colors of the image.
            It helps to identify distinct colors in the image.
    Step 3: Threshold the image based on the color using "inRange" function.
            Range of the color, which is considered as a defect for object, is
            passed as one of the argument to inRange function to create a mask.
    Step 4: Morphological opening and closing is done on the mask to remove
            noises and fill the gaps.
    Step 5: Find the contours on the mask image. Contours are filtered based on
            the area to get the contours of defective area. Contour of the
            defective area is then drawn on the original image to visualize.
    Step 6: Save the image in "color" folder if it has a color defect.

    :param frame: Input frame from the video
    :param cnt: Contours of the object
    :return: color_flag, defect
    """
    defect = "Color"
    global OBJECT_COUNT
    color_flag = False
    # Increase the brightness of the image
    cv2.convertScaleAbs(frame, frame, 1, 20)
    # Convert the captured frame from BGR to HSV
    img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Threshold the image
    img_threshold = cv2.inRange(img_hsv, LOWER_COLOR_RANGE, UPPER_COLOR_RANGE)
    # Morphological opening (remove small objects from the foreground)
    img_threshold = cv2.erode(img_threshold,
                              kernel=cv2.getStructuringElement(
                                  cv2.MORPH_ELLIPSE, (5, 5)))
    img_threshold = cv2.dilate(img_threshold,
                               kernel=cv2.getStructuringElement(
                                   cv2.MORPH_ELLIPSE, (5, 5)))
    contours, hierarchy = cv2.findContours(img_threshold, cv2.RETR_LIST,
                                           cv2.CHAIN_APPROX_NONE)
    for i in range(len(contours)):
        area = cv2.contourArea(contours[i])
        if 2000 < area < 10000:
            cv2.drawContours(frame, contours[i], -1, (0, 0, 255), 2)
            color_flag = True
    if color_flag:
        x, y, w, h = cv2.boundingRect(cnt)
        print("Color defect detected in object {}".format(COUNT_OBJECT))
        cv2.imwrite("{}/color/Color_{}.png".format(base_dir, COUNT_OBJECT),
                    frame[y : y + h, x : x + w])
        cv2.putText(frame, OBJECT_COUNT, (5, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Defect: {}".format(defect), (5, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Length (mm): {}".format(HEIGHT_OF_OBJ), (5, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Width (mm): {}".format(WIDTH_OF_OBJ), (5, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.imshow("Out", frame)
        cv2.waitKey(2000)
    return color_flag, defect


def detect_crack(frame, cnt):
    """
    Identify the Crack defect on the object.
    Step 1: Convert the image to gray scale.
    Step 2: Blur the gray image to remove the noises.
    Step 3: Find the edges on the blurred image to get the contours of
            possible cracks.
    Step 4: Filter the contours to get the contour of the crack.
    Step 5: Draw the contour on the orignal image for visualization.
    Step 6: Save the image in "crack" folder if it has crack defect.

    :param frame: Input frame from the video
    :param cnt: Contours of the object
    :return: defect_flag, defect, cnt
    """
    defect = "Crack"
    global OBJECT_COUNT
    defect_flag = False
    low_threshold = 130
    kernel_size = 3
    ratio = 3
    # Convert the captured frame from BGR to GRAY
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img = cv2.blur(img, (7, 7))
    # Find the edges
    detected_edges = cv2.Canny(img, low_threshold,
                               low_threshold * ratio, kernel_size)
    # Find the contours
    contours, hierarchy = cv2.findContours(detected_edges, cv2.RETR_TREE,
                                           cv2.CHAIN_APPROX_NONE)

    if len(contours) != 0:
        for i in range(len(contours)):
            area = cv2.contourArea(contours[i])
            if area > 20 or area < 9:
                cv2.drawContours(frame, contours, i, (0, 255, 0), 2)
                defect_flag = True

        if defect_flag:
            x, y, w, h = cv2.boundingRect(cnt)
            print("Crack defect detected in object {}".format(COUNT_OBJECT))
            cv2.imwrite("{}/crack/Crack_{}.png".format(base_dir, COUNT_OBJECT),
                        frame[y : y + h , x : x + w ])
            cv2.putText(frame, OBJECT_COUNT, (5, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        0.75, (255, 255, 255), 2)
            cv2.putText(frame, "Defect: {}".format(defect), (5, 140),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            cv2.putText(frame, "Length (mm): {}".format(HEIGHT_OF_OBJ),
                        (5, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            cv2.putText(frame, "Width (mm): {}".format(WIDTH_OF_OBJ), (5, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            cv2.imshow("Out", frame)
            cv2.waitKey(2000)
    return defect_flag, defect


def update_data(input_data):
    """
    To update database with input_data.
    Step 1: Write given data points to the database.
    Step 2: Use SELECT statement to query the database.

    :param input_data: JSON body consisting of object number and defect values
    """
    client.write_points([input_data])
    client.query('SELECT * from "obj_flaw_detector"')


def flaw_detection():
    """
    Measurement and defects such as color, crack and orientation of the object
    are found.

    :return: None
    """
    global HEIGHT_OF_OBJ
    global WIDTH_OF_OBJ
    global COUNT_OBJECT
    global OBJ_DEFECT
    global FRAME_COUNT
    global OBJECT_COUNT

    while cap.isOpened():
        # Read the frame from the stream
        ret, frame = cap.read()

        if not ret:
            break

        FRAME_COUNT += 1

        # Check every given frame number
        # (Number chosen based on the frequency of object on conveyor belt)
        if FRAME_COUNT % frame_number == 0:
            HEIGHT_OF_OBJ = 0
            WIDTH_OF_OBJ = 0
            OBJ_DEFECT = []
            data_base = []
            # Convert BGR image to HSV color space
            img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Thresholding of an Image in a color range
            img_threshold = cv2.inRange(img_hsv, (LOW_H, LOW_S, LOW_V),
                                        (HIGH_H, HIGH_S, HIGH_V))

            # Morphological opening(remove small objects from the foreground)
            img_threshold = cv2.erode(img_threshold,
                                      cv2.getStructuringElement(
                                          cv2.MORPH_ELLIPSE, (5, 5)))
            img_threshold = cv2.dilate(img_threshold,
                                       cv2.getStructuringElement(
                                           cv2.MORPH_ELLIPSE, (5, 5)))

            # Morphological closing(fill small holes in the foreground)
            img_threshold = cv2.dilate(img_threshold,
                                       cv2.getStructuringElement(
                                           cv2.MORPH_ELLIPSE, (5, 5)))
            img_threshold = cv2.erode(img_threshold,
                                      cv2.getStructuringElement(
                                          cv2.MORPH_ELLIPSE, (5, 5)))

            # Find the contours on the image
            contours, hierarchy = cv2.findContours(img_threshold,
                                                   cv2.RETR_LIST,
                                                   cv2.CHAIN_APPROX_NONE)

            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if OBJECT_AREA_MAX > w * h > OBJECT_AREA_MIN:
                    box = cv2.minAreaRect(cnt)
                    box = cv2.boxPoints(box)
                    height, width = dimensions(np.array(box, dtype='int'))
                    HEIGHT_OF_OBJ = round(height * one_pixel_length * 10, 2)
                    WIDTH_OF_OBJ = round(width * one_pixel_length * 10, 2)
                    COUNT_OBJECT += 1
                    frame_orient = frame.copy()
                    frame_clr = frame.copy()
                    frame_crack = frame.copy()
                    frame_nodefect = frame.copy()
                    OBJECT_COUNT = "Object Number : {}".format(COUNT_OBJECT)

                    # Check for the orientation of the object
                    orientation_flag, orientation_defect = \
                        detect_orientation(frame_orient, cnt)
                    if orientation_flag:
                        value = 1
                        data_base.append(value)
                        OBJ_DEFECT.append(str(orientation_defect))
                    else:
                        value = 0
                        data_base.append(value)

                    # Check for the color defect of the object
                    color_flag, color_defect = detect_color(frame_clr, cnt)
                    if color_flag:
                        value = 1
                        data_base.append(value)
                        OBJ_DEFECT.append(str(color_defect))
                    else:
                        value = 0
                        data_base.append(value)

                    # Check for the crack defect of the object
                    crack_flag, crack_defect = detect_crack(frame_crack, cnt)
                    if crack_flag:
                        value = 1
                        data_base.append(value)
                        OBJ_DEFECT.append(str(crack_defect))
                    else:
                        value = 0
                        data_base.append(value)

                    # Check if none of the defect is found
                    if not OBJ_DEFECT:
                        value = 1
                        data_base.append(value)
                        defect = "No Defect"
                        OBJ_DEFECT.append(defect)
                        print("No defect detected in object {}"
                              .format(COUNT_OBJECT))
                        cv2.putText(frame_nodefect, "Length (mm): {}".format(HEIGHT_OF_OBJ),
                                    (5, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                                    (255, 255, 255), 2)
                        cv2.putText(frame_nodefect, "Width (mm): {}".format(WIDTH_OF_OBJ),
                                    (5, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                                    (255, 255, 255), 2)
                        cv2.imwrite("{}/no_defect/Nodefect_{}.png".format(
                            base_dir, COUNT_OBJECT),
                                    frame[y : y + h,
                                          x : x + w])
                    else:
                        value = 0
                        data_base.append(value)
                    print("Length (mm) = {}, width (mm) = {}".format(
                        HEIGHT_OF_OBJ, WIDTH_OF_OBJ))
            if not OBJ_DEFECT:
                continue

            # Create json_body to store the defects
            else:
                json_body = {
                    "measurement": "obj_flaw_detector",
                    "tags": {
                        "user": "User"
                    },

                    "fields": {
                        "Object Number": COUNT_OBJECT,
                        "Orientation": data_base[0],
                        "Color": data_base[1],
                        "Crack": data_base[2],
                        "No defect": data_base[3]
                    }
                }
                # Send json_body to influxdb
                update_data(json_body)

        all_defects = " ".join(OBJ_DEFECT)
        cv2.putText(frame, "Press q to quit", (410, 50),
                    cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, OBJECT_COUNT, (5, 50), cv2.FONT_HERSHEY_SIMPLEX,
                    0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Defect: {}".format(all_defects), (5, 140),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Length (mm): {}".format(HEIGHT_OF_OBJ), (5, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.putText(frame, "Width (mm): {}".format(WIDTH_OF_OBJ), (5, 110),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        cv2.imshow("Out", frame)
        keypressed = cv2.waitKey(40)
        if keypressed == 113 or keypressed == 81:
            break
    cv2.destroyAllWindows()
    cap.release()


if __name__ == '__main__':

    args = build_argparser().parse_args()

    base_dir = args.directory

    if not base_dir:
        base_dir = os.getcwd()

    # Checks for the video file
    if args.input:
        if args.input == 'CAM':
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                print("\nCamera not plugged in... Exiting...\n")
                sys.exit(0)
            fps = cap.get(cv2.CAP_PROP_FPS)
            delay = (int)(1000 / fps)
        else:
            cap = cv2.VideoCapture(args.input)
            if not cap.isOpened():
                print("\nUnable to open video file... Exiting...\n")
                sys.exit(0)
            fps = cap.get(cv2.CAP_PROP_FPS)
            delay = (int)(1000 / fps)

        if args.distance and args.fieldofview:
            width_of_video = cap.get(3)
            height_of_video = cap.get(4)
            # Convert degrees to radians
            radians = (args.fieldofview / 2) * 0.0174533
            # Calculate the diagonal length of image in millimeters using
            # field of view of camera and distance between object and camera.
            diagonal_length_of_image_plane = abs(
                2 * (args.distance / 10) * math.tan(radians))
            # Calculate diagonal length of image in pixel
            diagonal_length_in_pixel = math.sqrt(
                math.pow(width_of_video, 2) + math.pow(height_of_video, 2))
            # Convert one pixel value in millimeters
            one_pixel_length = (diagonal_length_of_image_plane /
                                diagonal_length_in_pixel)
        # If distance between camera and object and field of view of camera
        # are not provided, then 96 pixels per inch is considered.
        # pixel_lengh = 2.54 cm (1 inch) / 96 pixels
        else:
            one_pixel_length = 0.0264583333
    else:
        print("\nPlease provide video input... Exiting...\n")

    dir_names = ["crack", "color", "orientation", "no_defect"]
    OBJ_DEFECT = []
    frame_number = 40
    FRAME_COUNT = 0

    # Get ipaddress from the get_ip_address
    ipaddress, port, proxy,  = get_ip_address()
    database = 'obj_flaw_database'
    client = InfluxDBClient(host=ipaddress, port=port,
                            database=database, proxies=proxy)
    client.create_database(database)

    # create folders with the given dir_names to save defective objects
    for i in range(len(dir_names)):
        if not os.path.exists(os.path.join(base_dir, dir_names[i])):
            os.makedirs(os.path.join(base_dir, dir_names[i]))
        else:
            file_list = os.listdir(os.path.join(base_dir, dir_names[i]))
            for f in file_list:
                os.remove(os.path.join(base_dir, dir_names[i], f))
    # Find dimensions and flaw detections such as color, crack and orientation
    # of the object.
    flaw_detection()
