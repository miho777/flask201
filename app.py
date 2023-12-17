#!/usr/bin/env python3
##################################################
# This is the main application file.
# It has been kept to a minimum using the design
# principles of Models, Views, Controllers (MVC).
##################################################
# Import modules required for app
import os
from flask import Flask, render_template, request
from models import get_photos, insert_photo, upload_photo, delete_db

# Create a Flask instance
app = Flask(__name__)

##### Define routes #####
@app.route('/')
def home():
    album_photos = get_photos()						# Call function to retrieve all photo's from database in 'models.py' 
    return render_template('default.html',album_photos=album_photos,url="home")

# This route accepts GET and POST calls
@app.route('/upload', methods=['POST'])
def upload():
	insert_photo(request)							# Call function to process the database transaction in 'models.py'
	upload_photo(request.files['photo'])			# Call function to upload photo to ECS in 'models.py'
	return render_template('submit-photo.html')		# Return a page to inform the user of a successful upload

@app.route('/photo/<path:photo>')
def photo(photo):
    return render_template('photo.html',photo=photo)

@app.route('/deletedb')
def delete():
	delete_db()										# for Debug to delete documents of MongoDB in 'models.py'
	return render_template('submit-photo.html')
##### Run the Flask instance, browse to http://<< Host IP or URL >>:5000 #####
if __name__ == "__main__":
	app.run(host='0.0.0.0', port=int(os.getenv('PORT', '5000')), threaded=True)