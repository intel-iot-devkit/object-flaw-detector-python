
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

import cv2
import argparse
import socket
import os

import numpy as np

from math import atan2
from influxdb import InfluxDBClient

# Lower and upper value of color Range of the object for color thresholding to detect the object

OBJECT_AREA = 9000
LOW_H = 0
LOW_S = 0
LOW_V = 47
HIGH_H = 179
HIGH_S = 255
HIGH_V = 255
LOWER_COLOR_RANGE = (0, 0, 0)
UPPER_COLOR_RANGE = (174, 73, 255)
count_object = 0


'''
**************************************************** IPAddress *********************************************************
 Gets the IP address of the machine using socket library
***********************************************************************************************************************
'''


def getIPAddress():
    hostname = socket.gethostname()
    ipaddress = socket.gethostbyname(hostname)
    port = 8086
    proxy = {"http": "http://{}:{}".format(ipaddress, port)}
    return ipaddress, port, proxy


'''
*********************************************** Orientation Defect detection ******************************************
 Step 1: Convert 3D matrix of contours to 2D 
 Step 2: Apply PCA algorithm to find angle of the data points.
 Step 3: If angle is greater than 0.5, return_flag is made to True else false. 
 Step 4: Save the image in "Orientation" folder if it has a orientation defect.
***********************************************************************************************************************
'''


def get_orientation(contours):
    """
    Gives the angle of the orientation of the object in radians
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
    Identifies the Orientation of the object based on the detected angle
    :param frame: Input frame from video
    :param contours: contour of the object from the frame
    :return: defect_flag, object_defect
    """
    object_defect = "Defect : Orientation"
    # Find the orientation of each contour
    angle = get_orientation(contours)
    # If angle is less than 0.5 then we conclude that no orientation defect is present
    if angle < 0.5:
        defect_flag = False
    else:
        x, y, w, h = cv2.boundingRect(contours)
        print("Orientation defect detected in object {}".format(count_object))
        defect_flag = True
        cv2.imwrite("{}/orientation/Orientation_{}.jpg".format(base_dir, count_object), frame[y - 5: y + h + 10, x - 5: x + w + 10])
        cv2.putText(frame, object_count, (5, 50), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, object_defect, (5, 130), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
        cv2.imshow("Out", frame)
        cv2.waitKey(2000)
    return defect_flag, object_defect


'''
*********************************************** Color Defect detection ************************************************
 Step 1: Increase the brightness of the image
 Step 2: Convert the image to HSV Format. HSV color space gives more information about the colors of the image. 
         It helps to identify distinct colors in the image.
 Step 3: Threshold the image based on the color using "inRange" function. Range of the color, which is considered as 
         a defect for the object, is passed as one of the argument to inRange function to create a mask
 Step 4: Morphological opening and closing is done on the mask to remove noises and fill the gaps
 Step 5: Find the contours on the mask image. Contours are filtered based on the area to get the contours of defective
         area. Contour of the defective area is then drawn on the original image to visualize.
 Step 6: Save the image in "color" folder if it has a color defect.
***********************************************************************************************************************
'''


def detect_color(frame, cnt):
    """
    Identifies the color defect W.R.T the set default color of the object
    :param frame: Input frame from the video
    :param cnt: Contours of the object
    :return: color_flag, object_defect
    """
    object_defect = "Defect : Color"
    color_flag = False
    # Increase the brightness of the image
    cv2.convertScaleAbs(frame, frame, 1, 20)
    # Convert the captured frame from BGR to HSV
    img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    # Threshold the image
    img_thresholded = cv2.inRange(img_hsv, LOWER_COLOR_RANGE, UPPER_COLOR_RANGE)
    # Morphological opening (remove small objects from the foreground)
    img_thresholded = cv2.erode(img_thresholded, kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    img_thresholded = cv2.dilate(img_thresholded, kernel=cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    _, contours, hierarchy = cv2.findContours(img_thresholded, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    for i in range(len(contours)):
        area = cv2.contourArea(contours[i])
        if 2000 < area < 10000:
            cv2.drawContours(frame, contours[i], -1, (0, 0, 255), 2)
            color_flag = True
    if color_flag == True:
        x,y,w,h =cv2.boundingRect(cnt)
        print("Color defect detected in object {}".format(count_object))
        cv2.imwrite("{}/color/Color_{}.jpg".format(base_dir, count_object), frame[y - 5: y + h + 10, x - 5: x + w + 10])
        cv2.putText(frame, object_count, (5, 50), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, object_defect, (5, 130), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
        cv2.imshow("Out", frame)
        cv2.waitKey(2000)
    return color_flag, object_defect


'''
**************************************************** Crack detection **************************************************
 Step 1: Convert the image to gray scale
 Step 2: Blur the gray image to remove the noises
 Step 3: Find the edges on the blurred image to get the contours of possible cracks
 Step 4: Filter the contours to get the contour of the crack
 Step 5: Draw the contour on the orignal image for visualization
 Step 6: Save the image in "crack" folder if it has crack defect
***********************************************************************************************************************
'''


def detect_crack(frame, cnt):
    """
    Identifies the Crack defect on the object
    :param frame: Input frame from the video
    :param cnt: Contours of the object
    :return: defect_flag, object_defect, cnt
    """
    object_defect = "Defect : Crack"
    defect_flag = False
    low_threshold = 130
    kernel_size = 3
    ratio = 3
    # Convert the captured frame from BGR to GRAY
    img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    img = cv2.blur(img, (7, 7))
    # Find the edges
    detected_edges = cv2.Canny(img, low_threshold, low_threshold * ratio, kernel_size)
    # Find the contours
    _, contours, hierarchy = cv2.findContours(detected_edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)

    if len(contours) != 0:
        for i in range(len(contours)):
            area = cv2.contourArea(contours[i])
            if area > 20 or area < 9:

                cv2.drawContours(frame, contours, i, (0, 255, 0), 2)
                defect_flag = True

        if defect_flag == True:
            x, y, w, h = cv2.boundingRect(cnt)
            print("Crack defect detected in object {}".format(count_object))
            cv2.imwrite("{}/crack/Crack_{}.jpg".format(base_dir, count_object), frame[y - 5: y + h + 20, x - 5: x + w + 10])
            cv2.putText(frame, object_count, (5, 50), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, object_defect, (5, 130), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
            cv2.imshow("Out", frame)
            cv2.waitKey(2000)
    return defect_flag, object_defect


'''
**************************************************** Influxdb *********************************************************
 Step 1: Launch Influxdb client
 Step 2: Create 'obj_flaw_database' database
 Step 3: Write given data points to the database
 Step 4: Use SELECT statement to query the database
***********************************************************************************************************************
'''


def update_data(input_data):
    """
    To update database with input_data
    :param input_data: JSON body consisting of object number and defect values
    """
    client.write_points([input_data])
    results = client.query('SELECT * from "obj_flaw_detector"')


if __name__ == '__main__':
    data = []
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--dir', required=False, help="Name of the directory to which defective images are saved")
    parser.add_argument('-f', '--vid', default=0, help="Name of the video file")
    args = vars(parser.parse_args())
    base_dir = args['dir']
    if base_dir == None:
       base_dir = os.getcwd()


    file = args['vid']
    # Checks for the video file
    if file != 0:
        path = file
        #path = os.path.join(base_dir, file)
    # Checks for the web cam feed
    else:
        path = 0

    dir_names = ["crack", "color", "orientation", "no_defect"]
    frame_count = 0
    num_of_dir = 4
    frame_number = 40
    defect = []

    # Get ipaddress from the getIPAddress
    ipaddress, port, proxy,  = getIPAddress()
    database = 'obj_flaw_database'
    client = InfluxDBClient(host=ipaddress, port=port, database=database, proxies=proxy)
    client.create_database(database)

    # create folders with the given dir_names to save defective objects
    for i in range(len(dir_names)):
        if not os.path.exists(os.path.join(base_dir, dir_names[i])):
            os.makedirs(os.path.join(base_dir, dir_names[i]))
        else:
            file_list = os.listdir(os.path.join(base_dir, dir_names[i]))
            for f in file_list:
                os.remove(os.path.join(base_dir,dir_names[i],f))

    capture = cv2.VideoCapture(path)

    # Check if video is loaded successfully
    if capture.isOpened():
        print("Opened video!!")

    else:
        print("Problem loading the video!!!")


    while True:
        # Read the frame from the stream
        _, frame = capture.read()

        if np.shape(frame) == ():
            break

        frame_count += 1
        object_count = "Object Number : {}".format(count_object)

        # Check every given frame number (Number chosen based on the frequency of object on conveyor belt)
        if frame_count % frame_number == 0:
            defect = []
            data_base = []

            # Convert BGR image to HSV color space
            img_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # Thresholding of an Image in a color range
            img_thresholded = cv2.inRange(img_hsv, (LOW_H, LOW_S, LOW_V), (HIGH_H, HIGH_S, HIGH_V))

            # Morphological opening(remove small objects from the foreground)
            img_thresholded = cv2.erode(img_thresholded, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            img_thresholded = cv2.dilate(img_thresholded, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

            # Morphological closing(fill small holes in the foreground)
            img_thresholded = cv2.dilate(img_thresholded, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
            img_thresholded = cv2.erode(img_thresholded, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

            # Find the contours on the image
            _, contours, hierarchy = cv2.findContours(img_thresholded, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)

            for cnt in contours:
                x, y, width, height = cv2.boundingRect(cnt)
                if width * height > OBJECT_AREA:
                    count_object += 1
                    frame_copy = frame.copy()
                    object_count = "Object Number : {}".format(count_object)

                    # Check for the orientation of the object
                    orientation_flag, orientation_defect = detect_orientation(frame, cnt)
                    if orientation_flag == True:
                        value = 1
                        data_base.append(value)
                        defect.append(str(orientation_defect))
                    else:
                        value = 0
                        data_base.append(value)

                    # Check for the color defect of the object
                    color_flag, color_defect = detect_color(frame, cnt)
                    if color_flag == True:
                        value = 1
                        data_base.append(value)
                        defect.append(str(color_defect))
                    else:
                        value = 0
                        data_base.append(value)

                    # Check for the crack defect of the object
                    crack_flag, crack_defect = detect_crack(frame_copy, cnt)
                    if crack_flag == True:
                        value = 1
                        data_base.append(value)
                        defect.append(str(crack_defect))
                    else:
                        value = 0
                        data_base.append(value)

                    # Check if none of the defect is found
                    if not defect:
                        value = 1
                        data_base.append(value)
                        object_defect = "No Defect"
                        defect.append(str(object_defect))
                        print("No defect detected in object {}".format(count_object))
                        cv2.imwrite("{}/no_defect/Nodefect_{}.jpg".format(base_dir, count_object), frame[y - 5: y + height + 10, x - 5: x + width + 10])
                    else:
                        value = 0
                        data_base.append(value)
            if not defect:
                continue

            # Create json_body to store the defects
            else:
                json_body = {
                    "measurement": "obj_flaw_detector",
                    "tags": {
                        "user": "User"
                    },

                    "fields": {
                        "Object Number": count_object,
                        "Orientation": data_base[0],
                        "Color": data_base[1],
                        "Crack": data_base[2],
                        "No defect": data_base[3]
                    }
                }
                # Send json_body to influxdb
                update_data(json_body)

        all_defects = " ".join(defect)

        cv2.putText(frame, all_defects, (5, 130), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
        cv2.putText(frame, object_count, (5, 50), cv2.FONT_HERSHEY_DUPLEX, 1, (255, 255, 255), 2)
        cv2.imshow("Out", frame)
        cv2.waitKey(40)













