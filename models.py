#!/usr/bin/env python3
##### This is the database processing file. (aka. Models) #####
# Import modules required for app
import os
import boto3
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from PIL import Image
from config import ecs_test_drive, piper_mongodb

### Remote MongoDB instance
DB_USER = piper_mongodb['mongodb_user']

### Set DB password
DB_PASSWORD = os.getenv('DB_PASSWORD','Need2SetDB_PASSWORD') 
# DB_PASSWORD = piper_mongodb['mongodb_password']

### Connect DB server
db_arg = "mongodb://" + DB_USER + ":" + DB_PASSWORD + "@cluster0-shard-00-00.jnkoj.mongodb.net:27017,cluster0-shard-00-01.jnkoj.mongodb.net:27017,cluster0-shard-00-02.jnkoj.mongodb.net:27017/?ssl=true&replicaSet=atlas-10dctt-shard-0&authSource=admin&retryWrites=true&w=majority"
client = MongoClient(db_arg)

### Set DB name: Make sure this create your unique MongoDB database name ###
#DB_NAME = os.getenv('DB_NAME','Need2SetDB_NAME')   ### e.g. P2023_NMiho  
DB_NAME = piper_mongodb['mongodb_name']  

### Open DB with database name
db = client[DB_NAME]

# Remove any existing documents in photos collection
# db.photos.delete_many({})   # Comment this line if you don't want to remove documents each time you start the app

### Retrieve all photos records from database
def get_photos():
    return db.photos.find({})

### Insert form fields into database
def insert_photo(request):
    title = request.form['title']
    comments = request.form['comments']
    filename = secure_filename(request.files['photo'].filename)
    thumbfile = filename.rsplit(".",1)[0] + "-thumb.jpg"
    # ecs_access_key_id = os.getenv('ECS_ID','Need2SetECS_ID') 
    # photo_url = "http://" + ecs_access_key_id.split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + filename
    # thumbnail_url = "http://" + ecs_access_key_id.split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + thumbfile
    photo_url = "http://" + ecs_test_drive['ecs_access_key_id'].split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + filename
    thumbnail_url = "http://" + ecs_test_drive['ecs_access_key_id'].split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + thumbfile

    db.photos.insert_one({'title':title, 'comments':comments, 'photo':photo_url, 'thumb':thumbnail_url})

def upload_photo(file):
    # Get ECS credentials from external config file
    ecs_endpoint_url = ecs_test_drive['ecs_endpoint_url']
    # ecs_access_key_id = os.getenv('ECS_ID','Need2SetECS_ID')                ### Set Own ECS ID
    ecs_access_key_id = ecs_test_drive['ecs_access_key_id']
    ecs_secret_key = os.getenv('ECS_SECRET_KEY','Need2SetECS_SECRET_KEY')   ### Set Own ECS SECRET
    # ecs_secret_key = ecs_test_drive['ecs_secret_key']
    ecs_bucket_name = ecs_test_drive['ecs_bucket_name']

    # Open a session with ECS using the S3 API
    session = boto3.resource(service_name='s3', aws_access_key_id=ecs_access_key_id, aws_secret_access_key=ecs_secret_key, endpoint_url=ecs_endpoint_url)

    # Remove unsupported characters from filename
    filename = secure_filename(file.filename)

    # First save the file locally
    file.save(os.path.join("uploads", filename))

    # Create a thumbnail
    size = 225, 225
    with open("uploads/" + filename, 'rb') as f:
        img = Image.open(f)
        img.thumbnail(size)
        thumbfile = filename.rsplit(".",1)[0] + "-thumb.jpg"
        img.save("uploads/" + thumbfile,"JPEG")
        img.close()

    # Empty the variables to prevent memory leaks
    img = None

    ## Upload the original image to ECS
    session.Object(ecs_bucket_name, filename).put(Body=open("uploads/" + filename, 'rb'), ACL='public-read')

    ## Upload the thumbnail to ECS
    session.Object(ecs_bucket_name, thumbfile).put(Body=open("uploads/" + thumbfile, 'rb'), ACL='public-read')

    # Delete the local files
    os.remove("uploads/" + filename)
    os.remove("uploads/" + thumbfile)

###  for debug to delete all documents in MongoDB
def delete_db():
    db.photos.delete_many({}) 
