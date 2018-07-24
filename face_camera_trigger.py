#!/usr/bin/env python3
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Trigger PiCamera when face is detected."""

from aiy.vision.inference import CameraInference
from aiy.vision.models import face_detection
from picamera import PiCamera

import uuid
import time
import decimal

import boto3
from datetime import datetime
from time import sleep

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
rekog_client = boto3.client('rekognition')

s3_bucket = "hackerthon-stored-video-frame-images"
s3_key_frames_root = "images/"

camera_name = "Lido deck - Forward"

ddb_table = dynamodb.Table("EnrichedFrame")
ddb_table_found_face = dynamodb.Table("found-faces")
ddb_table_recognized_faces = dynamodb.Table("recognizedfaces")

def main():
    with PiCamera() as camera:
        # Configure camera
        camera.resolution = (1640, 922)  # Full Frame, 16:9 (Camera v2)
        camera.start_preview()

        # Do inference on VisionBonnet
        with CameraInference(face_detection.model()) as inference:
            for result in inference.run():
                faces=face_detection.get_faces(result)
                print('num_faces=%d' % len(faces))

                table = dynamodb.Table('PeopleCount')
                table.put_item(
                    Item={
                        'Location': 'Carnival Horizon Multiplex',
                        'TimeStamp': str(datetime.now().timestamp()),
                        'Count': str(len(faces)),
                    })

                if len(faces) >= 1:
                    camera.capture('faces.jpg')
                    approx_capture_timestamp = decimal.Decimal(time.time())
                    image_id = str(uuid.uuid4())
 
                    now = datetime.now()
                    year = now.strftime("%Y")
                    mon = now.strftime("%m")
                    day = now.strftime("%d")
                    hour = now.strftime("%H")

                    s3_key = (s3_key_frames_root + '{}/{}/{}/{}/{}.jpg').format(year, mon, day, hour, image_id)
                    s3_client.upload_file(
                        'faces.jpg',
                        Bucket=s3_bucket,
                        Key=s3_key
                    )

                    rekog_response = rekog_client.detect_faces(
                        Image={
                            'S3Object': {
                                'Bucket': s3_bucket,
                                'Name': s3_key
                             }
                        }  
                    )
                    print(rekog_response)
                    if len(rekog_response['FaceDetails']) > 0:  
                        response = rekog_client.search_faces_by_image(
                            CollectionId='face_rekognition_collection',
                            Image={ 
                                'S3Object': {
                                    'Bucket': s3_bucket,
                                    'Name': s3_key
                                }
                            }
                        )
                
                        for match in response['FaceMatches']:
                            print ("match found")
                            print (match['Face']['FaceId'],match['Face']['Confidence'])
                    
                            face = ddb_table_recognized_faces.get_item(
                                TableName='recognizedfaces',  
                                Key={'RekognitionId': match['Face']['FaceId']}
                            )
                            if 'Item' in face:
                               print (face)
                               faceTimeLocation_id = str(uuid.uuid4())
                               processed_timestamp = decimal.Decimal(time.time())
                               item = {
                                   'faceTimeLocation_id': faceTimeLocation_id,
                                   'faceId': str(match['Face']['FaceId']),
                                   'confidence': str(match['Face']['Confidence']),
                                   'fullName': face['Item']['FullName'],
                                   'processed_timestamp' : processed_timestamp,
                                   'approx_capture_timestamp' : approx_capture_timestamp,
                                   's3_bucket': s3_bucket,
                                   's3_key': s3_key,
                                   'camera_name': camera_name
                               }
                               ddb_table_found_face.put_item(Item=item)
                               print(item)
                    else:
                        print ('no match found in person lookup')

                sleep(1)

        # Stop preview
        camera.stop_preview()


if __name__ == '__main__':
    main()
