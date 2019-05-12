

# Object Flaw Detector

| Details               |                   |
| --------------------- | ----------------- |
| Target OS:            | Ubuntu* 16.04 LTS |
| Programming Language: | Python* 3.5       |
| Time to complete:     | 30 min            |

This reference implementation is also [available in C++](https://github.com/intel-iot-devkit/reference-implementation-private/blob/object-flaw-measurement/object-flaw-detector-measurement/README.MD).

## Introduction

The object flaw detector application detects the anomalies such as color, crack, and orientation of the object moving on a conveyor belt. Anomalies are marked as defective and saved in the color, crack, orientation folders respectively. Also objects with no defects are saved in no_defect folder.
These anomalies data is sent to InfluxDB* database and is visualized on Grafana*.
This application also measures length and width of the object in millimeters.  

## Requirements

- Ubuntu 16.04
- Intel® Distribution of OpenVINO™ toolkit 2019 R1 Release
- Grafana* v5.3.2 
- InfluxDB* v1.6.2

## Setup

### Install Intel® Distribution of OpenVINO™ toolkit 

Refer to [ Install the Intel® Distribution of OpenVINO™ toolkit for Linux*](https://software.intel.com/en-us/articles/OpenVINO-Install-Linux) for more information on how to install and set up the Intel® Distribution of OpenVINO™ toolkit

### Install InfluxDB* 

Use the commands below to install InfluxDB:

```
   sudo apt install curl
   sudo curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add - 
   source /etc/lsb-release
   echo "deb https://repos.influxdata.com/${DISTRIB_ID,,} ${DISTRIB_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/influxdb.list
   sudo apt-get update 
   sudo apt-get install influxdb
   sudo service influxdb start
```

### Install Grafana*

Use the commands below to install Grafana:

```
   wget https://s3-us-west-2.amazonaws.com/grafana-releases/release/grafana_5.3.2_amd64.deb
   sudo apt-get install -y adduser libfontconfig
   sudo dpkg -i grafana_5.3.2_amd64.deb
   sudo /bin/systemctl start grafana-server
```

### Install Python* Package Dependencies

- InfluxDB 

- Numpy

  Run the following commands to install the Python dependencies:

  ```
    sudo apt-get install python3-pip
    pip3 install influxdb
    pip3 install numpy
    pip3 install jupyter
  ```

## How It works

This application takes the input from a video camera or a video file for processing.

![Data Flow Diagram](./images/dataFlow.png)

**Orientation defect detection:** Get the frame and change the color space to HSV format. Threshold the image based on the color of the object using [inRange](https://docs.opencv.org/master/df/d9d/tutorial_py_colorspaces.html) function to create a mask. Perform morphological opening and closing on the mask and find the contours using [findContours](https://docs.opencv.org/master/d4/d73/tutorial_py_contours_begin.html) function. Filter the contours based on the area. Perform [PCA](https://docs.opencv.org/master/d1/dee/tutorial_introduction_to_pca.html) (Principal Component Analysis) on the contours to get the orientation of the object.

![orientation](./images/orientation.jpg)

**Color defect detection:** Threshold the image based on the defective color of the object using  [inRange](https://docs.opencv.org/master/df/d9d/tutorial_py_colorspaces.html) function. Use the mask obtained from the  [inRange](https://docs.opencv.org/master/df/d9d/tutorial_py_colorspaces.html) function to find the defective area.

![color](./images/color.jpg)

**Crack detection:** Transform the image from BGR to Grayscale format using [cvtColor](https://docs.opencv.org/master/df/d9d/tutorial_py_colorspaces.html) function. Blur the image using [blur](https://docs.opencv.org/master/d4/d13/tutorial_py_filtering.html) function to remove the noises. Use the contours found on the blurred image to detect the cracks.

![crack](./images/crack.jpg)

Save the images of defective objects in their respective folders. For example, objects with color defect are saved in **color** folder, objects with cracks are saved in **crack** folder, objects with orientation defect are saved in **orientation** folder and objects with no defect are stored in **no_defect** folder.

## Set the Build Environment

Configure the environment to use the Intel® Distribution of OpenVINO™ toolkit by exporting environment variables:

```source /opt/intel/openvino/bin/setupvars.sh -pyver 3.5```

## Run the Code

- Go to object-flaw-detector-python directory:

  ```cd <path_to_object-flaw-detector-python_directory>```

- To see a list of the help options:

  ```python3 flawdetector.py --help``` 

- Input source can be a video file or a camera.

  - If using the video input from a file, run the command below:

    - To save defective images in a specific directory

      ```python3.5 flawdetector.py -dir <path_to_the_directory_to_dump_defective_images> -i data/object-flaw-detector.mp4```

    - To save defective images in current working directory

      ```python3.5 flawdetector.py -i data/object-flaw-detector.mp4```

  - If using a live feed from camera, run the command below:

    - To save defective images in a specific directory

      ```python3.5 flawdetector.py -dir <path_to_the_directory_to_dump_defective_images> -i CAM```

    - To save defective images in current working directory

      ```python3.5 flawdetector.py -i CAM```

    **Optional:** If field of view and distance between the object and camera are available use ```-fv```  and ```-dis``` command line arguments respectively. Otherwise camera of 96 pixels per inch is considered by default. For example:

       ```python3.5 flawdetector.py -i data/object-flaw-detector.mp4 -f 60 -d 50```

     **Note:** User can get field of view from camera specifications. The values for ```-f``` and ```-d``` should be in __degrees__ and __millimeters__ respectively.

- To check the data on InfluxDB, run the following commands:

  ```influx```

  ```show databases```

  ```use obj_flaw_database```

  ```select * from obj_flaw_detector```

### Data Visualization

- If you wish to import settings to visualise the data on Grafana, follow steps below.

  1. On the terminal, run the following command:

     ```sudo service grafana-server start```

  2. In your browser, go to localhost:3000.

  3. Log in with user as **admin** and password as **admin**.

  4. Click on **Configuration**.

  5. Select **“Data Sources”**.

  6. Click on **“+ Add data source”** and provide inputs below.

     - *Name*: Obj_flaw_detector
     - *Type*: InfluxDB
     - *URL*: http://localhost:8086
     - *Database*: obj_flaw_database
     - Click on “Save and Test”

  7. Click on **+**  icon present on the left side of the browser, select **import**.

  8. Click on **Upload.json File**.

  9. Select the file name "flaw_detector.json" from object-flaw-detector-python directory.

  10. Click on import.

  11. Run the python code again on the terminal to visualize data on grafana.

- If you wish to start from scratch to visualize data on Grafana, follow the steps below.

  1. On the terminal, run the following command.

     ```sudo service grafana-server start```

  2. Open the browser, go to **localhost:3000**.

  3. Log in with user as **admin** and password as **admin**.

  4. Click on the **Configuration** icon and  Select **“Data Sources”**.

  5. Click on **“+ Add data source”** and provide inputs below.

     - *Name*: Obj_flaw_detector
     - *Type*: InfluxDB
     - *URL*: http://localhost:8086
     - *Database*: obj_flaw_database
     - Click on “Save and Test”

      ![Grafana1](./images/grafana1.png)

  6. To create a new Dashboard

     - Select **+** icon from the side menu bar which is under grafana icon and select **Dashboard**.
     - Select **Graph**, click on the **Panel Title** and select **Edit**.
     - On the **Metrics** tab
       1. From **Datasource** choose **obj_flaw_detector**.
       2. Click on the row just below the tab, starting with **“A”**.
       3. Click on **select measurement** and select **obj_flaw_detector**.
       4. From **SELECT** row, click on **fields** and select **Color**. Also click on **+** from the same row, select **aggregations** and click on **distinct()**. From **GROUP BY** row, click on **time** and select **1s**. Name the query as **color** in the **ALIAS BY** row.
       5. Similarly from **Metrics** tab configure for **Crack**, **Orientation**, **No defect** and **Object Number** by clicking **Add Query**.
     - On the **Time range** tab, change the **override relative time** to **100s**.
     - Save the dashboard with name **flaw_detector**.

     ![Grafana2](./images/grafana2.png)

  7. Click on the **add panel** icon on the top menu.

     - Select **Table** , Click on the **Panel Title** and select **Edit** and follow the steps mentioned in the previous step for configuring **Metric** and **Time range** tab.
     - From the **Column Styles** tab, click on **+Add** and in the **Apply to columns named** give the name **color**, and also value **0** in the **Decimals**.
     - Similarly from **Column Styles** tab configure for **Crack**, **Orientation**, **No defect** and **Object Number** by clicking **+Add**.
     - Save the dashboard and click on **Back to dashboard** icon which is on right corner of the top menu.

  8. Click on the **add panel** icon on the top menu. 

     - Select **Singlestat**, Click on the **Panel Title** and select **Edit**. 
       1. From **Datasource** choose **obj_flaw_detector** and click on the row just below the tab, starting with **“A”**.
       2. Click on **select measurement** and select **obj_flaw_detector**. 
       3. From **SELECT** row, click on **fields** and select **Object Number**. Also click on **+** from the same row, select **aggregations** and click on **sum()**. From **GROUP BY** row, click on **time** and select **1s**. Name the query as **Object Count** in the **ALIAS BY** row.
     - On the **Options** tab, select **show** under **Gauge** option  and change the value of **decimals** to **0** under **Value** option.
     - Save the dashboard and click on **Back to dashboard** icon. 

  9. Mark the current directory as favourite by clicking on **Mark as favorite** icon on the top menu.

  10. Select **Time picker** from the top menu of dashboard. Under **Custom range** change the **From** value to **now-10s** and **Refreshing every:** to **5s**, click on **Apply** and save the dashboard.

  11. For re-testing, follow the steps below:

      - In a new browser tab or window, go to **http://localhost:3000/**. 
      - Log in with user as **admin** and password as **admin**.
      - The **“Home Dashboard”** shows up the list of starred and Recently viewed dashboards. Select **flaw_detector**. 

      ![Grafana3](./images/grafana3.png)

  12. Run the Python code again on the terminal to visualize data on Grafana.

      ![Grafana4](./images/grafana4.png) 

## (Optional) Save Data to the Cloud

As an optional step, send data results to an Amazon Web Services (AWS)* instance for graphing.

1. Make an EC2 Linux* instance on AWS. Steps are found [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/EC2_GetStarted.html).
2. Install InfluxDB on EC2 Linux instance. Download [here](https://github.com/influxdata/influxdb).
3. Download and install Grafana on EC2 Linux instance.  Download [here](https://grafana.com/get).
