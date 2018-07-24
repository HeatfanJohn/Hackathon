# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Licensed under the Amazon Software License (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
#     http://aws.amazon.com/asl/
# or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, express or implied. See the License for the specific language governing permissions and limitations under the License.

import urllib
import sys
import datetime
import base64
import boto3
import json
import cPickle
#import cv2
from multiprocessing import Pool
#import numpy as np
import code
import time
#import pytz
import uuid
import os

kinesis_client = boto3.client("kinesis")
rekog_client = boto3.client("rekognition")

#Frame capture parameters
default_capture_rate = 30 #frame capture rate.. every X frames. Positive integer.

#Rekognition paramters
rekog_max_labels = 123
rekog_min_conf = 50.0


#Send frame to Kinesis stream
def send_jpg(frame_jpg, frame_count, enable_kinesis=True, enable_rekog=False, write_file=True):
    try:
        #utc_dt = pytz.utc.localize(datetime.datetime.now())
        now_ts_utc = time.time() 
        #(utc_dt - datetime.datetime(1970, 1, 1, tzinfo=pytz.utc)).total_seconds()

        frame_package = {
            'ApproximateCaptureTime' : now_ts_utc,
            'FrameCount' : frame_count,
            'ImageBytes' : frame_jpg
        }

        if write_file:
            print("Writing file img_{}.jpg".format(frame_count))
            target = open("img_{}.jpg".format(frame_count), 'w')
            target.write(frame_jpg)
            target.close()

        #put encoded image in kinesis stream
        if enable_kinesis:
            print("Sending image to Kinesis")
            response = kinesis_client.put_record(
                StreamName="hephaestus",
                Data=cPickle.dumps(frame_package),
                PartitionKey="LidoPoolForward"
            )
            print(response)

        if enable_rekog:
            response = rekog_client.detect_labels(
                Image={
                    'Bytes': frame_jpg
                },
                MaxLabels=rekog_max_labels,
                MinConfidence=rekog_min_conf
            )
            print(response)

    except Exception as e:
        print( e )


def main():
    jpg_filename = "/tmp/{}.jpg".format(uuid.uuid1())
    uvc_command = "~/uvccapture/uvccapture -o{} -m -x960 -y544 -j10 -B40 -S120 -C50".format(
        jpg_filename )

    frame_count = 0
    while True:
        retvalue = os.system( uvc_command )
        if retvalue == 0:
            fh = open( jpg_filename, 'rb' )
            frame_jpg_bytes = bytearray( fh.read() )
            fh.close

            #Send to Kinesis
            send_jpg( frame_jpg_bytes, frame_count, True, False, False )

            frame_count += 1
        else:
            print( "Command " + uvc_command + " returned " + str(retvalue) )

        time.sleep( 10 )
if __name__ == '__main__':
    main()
