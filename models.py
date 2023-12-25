#!/usr/bin/env python3
##### This is the database processing file. (aka. Models) #####
# Import modules required for app
import os
import boto3
from botocore.exceptions import ClientError
from pymongo import MongoClient
from werkzeug.utils import secure_filename
from PIL import Image
from config import ecs_test_drive, piper_mongodb
import logging

### Define passcode mode
PASS_ENV = True     ### True:environment or False:config.py

### ログの設定
logging.basicConfig(filename='debug.log', level=logging.INFO)  ## DEBUG or INFO
### コンソールにもログを表示するためのハンドラを追加
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(console_handler)
# デバッグメッセージの出力
logging.info('START models.py debug message...')

### Remote MongoDB instance
DB_USER = piper_mongodb['mongodb_user']

### Set DB password
if PASS_ENV:
    DB_PASSWORD = os.getenv('DB_PASSWORD','Need2SetDB_PASSWORD') 
else:
    DB_PASSWORD = piper_mongodb['mongodb_password']

### Set DB information
db_arg = "mongodb://" + DB_USER + ":" + DB_PASSWORD + "@cluster0-shard-00-00.jnkoj.mongodb.net:27017,cluster0-shard-00-01.jnkoj.mongodb.net:27017,cluster0-shard-00-02.jnkoj.mongodb.net:27017/?ssl=true&replicaSet=atlas-10dctt-shard-0&authSource=admin&retryWrites=true&w=majority"

### Set DB name: Make sure this create your unique MongoDB database name ###
DB_NAME = piper_mongodb['mongodb_name']  

try:
    ### Connect MongoDB
    client = MongoClient(db_arg)
    logging.info('MongoClient(db_arg):' + db_arg)
    ### Open DB with database name
    db = client[DB_NAME]
    ### MongoDBデータベースへのアクセスを試みる
    db_names = client.list_database_names()
    logging.info('MongoDB connection successful:' + DB_NAME)
except Exception as e:              ### DB access fail:例外が発生
    logging.info("MongoDB connection failed:" + str(e))

### Remove any existing documents in photos collection
# db.photos.delete_many({})   # Comment this line if you don't want to remove documents each time you start the app

### Retrieve all photos records from database
def get_photos():
    return db.photos.find({})

### Insert form fields into database
def insert_photo(request):
    title = request.form['title']
    comments = request.form['comments']
    filename = secure_filename(request.files['photo'].filename)
    logging.info('Photo filename for DB:' + filename)
    if not filename:  ## ブランクの場合 return
        logging.info('*** Have to choose Photo ***')
        return False

    ### Check file extension
    dam_name , file_extension = os.path.splitext(filename)
    file_extension = file_extension.lower()

    if file_extension in ['.jpg', '.jpeg']:
        thumbfile = filename.rsplit(".", 1)[0] + "-thumb.jpg"
    elif file_extension == '.png':
        thumbfile = filename.rsplit(".", 1)[0] + "-thumb.png"
    logging.info('Photo thumb name for DB:' + thumbfile)

    # ecs_access_key_id = os.getenv('ECS_ID','Need2SetECS_ID') 
    # photo_url = "http://" + ecs_access_key_id.split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + filename
    # thumbnail_url = "http://" + ecs_access_key_id.split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + thumbfile
    photo_url = "http://" + ecs_test_drive['ecs_access_key_id'].split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + filename
    thumbnail_url = "http://" + ecs_test_drive['ecs_access_key_id'].split('@')[0] + ".public.ecstestdrive.com/" + ecs_test_drive['ecs_bucket_name'] + "/" + thumbfile

    db.photos.insert_one({'title':title, 'comments':comments, 'photo':photo_url, 'thumb':thumbnail_url})
    return True

### Upload photo and thumbnail to ECS
def upload_photo(file):
    ### Remove unsupported characters from filename
    filename = secure_filename(file.filename)
    if not filename:  ## ブランクの場合 return
        return
    ### First save the file locally
    file_path = os.path.join("uploads/", filename)
    file.save(file_path)

    ### Check file extension
    dam_name , file_extension = os.path.splitext(filename)
    #file_extension = os.path.splitext(filename)
    file_extension = file_extension.lower()

    ### Create a thumbnail
    size = 225, 225
    with open(file_path, 'rb') as f:
        img = Image.open(f)
        img.thumbnail(size)

        if file_extension in ['.jpg', '.jpeg']:
            thumbfile = filename.rsplit(".", 1)[0] + "-thumb.jpg"
            img.save(os.path.join("uploads/", thumbfile), "JPEG")
        elif file_extension == '.png':
            thumbfile = filename.rsplit(".", 1)[0] + "-thumb.png"
            img.save(os.path.join("uploads/", thumbfile), "PNG")
        logging.info('Photo thumb name for ECS:' + thumbfile)

        img.close()

    ### Empty the variables to prevent memory leaks
    img = None

    ### Get ECS credentials from external config file
    ecs_endpoint_url = ecs_test_drive['ecs_endpoint_url']
    ecs_access_key_id = ecs_test_drive['ecs_access_key_id']
    ecs_bucket_name = ecs_test_drive['ecs_bucket_name']
    if PASS_ENV:
        ecs_secret_key = os.getenv('ECS_SECRET_KEY','Need2SetECS_SECRET_KEY')   ### Set Own ECS SECRET
    else:
        ecs_secret_key = ecs_test_drive['ecs_secret_key']

    ### Open a session with ECS using the S3 API
    session = boto3.resource(
        service_name='s3',
        aws_access_key_id=ecs_access_key_id,
        aws_secret_access_key=ecs_secret_key,
        endpoint_url=ecs_endpoint_url
    )

    ### Upload the original image to ECS
    ### アップロード対象のファイルパス
    local_file_path = "uploads/" + filename
    try:
        session.Object(ecs_bucket_name, filename).put(Body=open(local_file_path, 'rb'), ACL='public-read')
        logging.info('Uploaded photo to ECS:' + local_file_path)
    except ClientError as e:
        logging.info('Upload fail photo to ECS:' + local_file_path +";" + e)

    ## Upload the thumbnail to ECS
    ### アップロード対象のファイルパス
    local_file_path = "uploads/" + thumbfile
    try:
        session.Object(ecs_bucket_name, thumbfile).put(Body=open(local_file_path, 'rb'), ACL='public-read')
        logging.info('Uploaded thumbfile to ECS:' + local_file_path)
    except ClientError as e:
        logging.info('Upload fail thumbfile to ECS:' + local_file_path +";" + e)

    # Delete the local files
    os.remove("uploads/" + filename)
    os.remove("uploads/" + thumbfile)

###  for debug to delete all documents in MongoDB
def delete_db():
    db.photos.delete_many({}) 
    logging.info('Deleted all documents in DB')