#!/usr/bin/python

__author__ = "Alex Leavitt, Abe Kazemzadeh"
__copyright__ = "Copyright 2013, University of Southern California"
__credits__ = []
__license__ = "http://www.apache.org/licenses/LICENSE-2.0"
__version__ = "1.0"
__maintainer__ = "last modified by Alex Leavitt"
__email__ = "aleavitt [at] usc [dot] edu"

import flask
from flask import Flask
from flask import render_template, request, redirect, url_for
from pymongo import MongoClient
import random
from collections import defaultdict
from config import * # config file with usernames, passwords, hosts, etc.

# for setting up the host name
import subprocess
import sys
host = subprocess.check_output('hostname').strip()
try:
    dns = subprocess.check_output('dnsdomainname').strip()
    if dns:
        host = host + '.' + dns
    else:
        host = subprocess.check_output('hostname -i').strip()
except OSError:
    pass # this happens when you are on a computer not set up as a server 
    
    
    
app = Flask(__name__)
app.secret_key = CONFIGSECRET_KEY
css = '/static/style.css'

MAX_ANNOTATIONS = 5 # set to how many annotations you want each user to perform per task



@app.route("/")
def start():
#     blob = flask.request.cookies
#     blob = flask.request.environ
    return render_template('welcome.html', next="/login")#, blob=blob)



@app.route("/annotate", methods=['POST', 'GET'])
def annotate():
#     blob = flask.request.cookies
#     blob = flask.request.environ

    sessionid = flask.session.get('sessionid')
    count = flask.session.get('count') # get annotation count from session


    # setting up the database
    host = CONFIGHOST
    connection = MongoClient(host)
    db = connection.sasa #change this to your respective database
    db.authenticate(CONFIGMONGOUSER,CONFIGMONGOPW)
    collection = db.orange #change this to your tweet storage mongo collection
    
    # finding a random tweet; this techniques is adapted from Michael's answer at http://stackoverflow.com/questions/2824157/random-record-from-mongodb
    rand_query = random.random()
    print rand_query
    query_result = collection.find_one({'rand':{"$gte":rand_query}})
    if query_result == None:
        query_result = collection.find_one({'rand':{"$lte":rand_query}})

    # setting variables from the tweet storage collection
    # these results might depend on how you set up your mongo database; change if necessary
    tweet_text = query_result['body']
    tweet_created_at = query_result['postedTimeObj']
    doc_id = query_result['_id']
    twusername  = query_result['actor']['preferredUsername']
    user_bio = query_result['actor']['summary']
    user_avatar_url = query_result['actor']['image']
    user_url = query_result['actor']['link']   
    stimulus = tweet_text #for generalization purposes
    
    # check form fields to see if annotator inputted necessary fields
    requiredFields = ['stimulus',
                        'sentiment',
                        ]
    additionalFields = ['missclassification',
                        'comparison',
                        'nonenglish']
    err = 0    
    returned_form_items_list = []
    for x in flask.request.form.keys():
        returned_form_items_list.append(x)
    
    print flask.request.form
    print returned_form_items_list
    print requiredFields
    
    error_message = ""    
    if count == 0:
        error_message = "basic error 0"  
    else:
        if set(requiredFields).issubset(set(returned_form_items_list)):
            print "it does all match!"
            err = 2
        else:
            err = 1
            print "it doesn't all match..."
        if err == 1:
            error_message = "One or more of the necessary form elements were skipped last time."
        elif err == 2:
            error_message = "All the submitted form elements were there."

    
    if request.method == 'POST':
        count += 1
        flask.session['count'] = count # save incremented count to session
    
        anno_collection = db.orange_annotated #set new collection for annotation data
        #these variables depend on your questions -- check annotate.html
        misclassification_response = flask.request.form.get('misclassification')
        comparison_response = flask.request.form.get('comparison')
        sentiment_response = flask.request.form.get('sentiment')
        nonenglish_response = flask.request.form.get('nonenglish')
        
        sessionid = str(sessionid) #otherwise mongo recognizes this as a binary type
        
        #inserting data into database
        annotated_results = [{"author":twusername,
                                "tweet_text":tweet_text,
                                "orig_id":doc_id,
                                "session_id":sessionid,
                                "misclassification":misclassification_response,
                                "comparison":comparison_response,
                                "sentiment":sentiment_response,
                                "nonenglish":nonenglish_response,
                                "annotation_count":count
                                }]          
        anno_collection.insert(annotated_results)
        
        #if the user has completed the necessary amount of annotations
        if flask.session.get('count') >= MAX_ANNOTATIONS:
            return flask.redirect(flask.url_for("logout"))  
    
    return render_template('annotate.html', 
                           next="/annotate",
                           #css=css, 
                           #blob=blob,
                           stimulus=stimulus,
                           error_message=error_message,
                           sessionid=sessionid,
                           count=count,
                           testvar=testvar,
                           tweet_text=tweet_text,
                           tweet_created_at=tweet_created_at, 
                           twusername=twusername,
                           user_bio=user_bio, 
                           user_avatar_url=user_avatar_url, 
                           user_url=user_url
                           )



@app.route("/login", methods=['POST', 'GET'])
def login():
    #blob = flask.request.cookies
    blob = flask.request.environ
    
    if not flask.request.args.get('sessionid'):
            #set username, session id, and count=0 in cookie
            import uuid
            flask.session['sessionid'] = uuid.uuid4()
            flask.session['count'] = 0
            
            # setting up another database for storing annotator user data
            host = CONFIGHOST
            connection = MongoClient(host)
            db = connection.sasa
            db.authenticate(CONFIGMONGOUSER,CONFIGMONGOPW)          
            annouser_collection = db.orange_annotators
            
            sessionid = flask.session.get('sessionid')
            sessionid = str(sessionid)
            
            if request.method == 'POST':
                anno_collection = db.orange_annotated
                annotator_age = flask.request.form.get('age')
                try: annotator_age = int(annotator_age) #otherwise integers store as string
                except ValueError: annotator_age = str(annotator_age)
                annotator_gender = flask.request.form.get('gender')
                annotator_language = flask.request.form.get('nativeLanguage')
                annotator_country = flask.request.form.get('countryOfResidence')
            
                annouser_results = [{"session_id":sessionid,
                                    "annotator_age":annotator_age,
                                    "annotator_gender":annotator_gender,
                                    "annotator_language":annotator_language,
                                    "annotator_country":annotator_country
                                    }]
                annouser_collection.insert(annouser_results)
            
            return flask.redirect(flask.url_for('annotate'))
    else:
        return flask.redirect(flask.url_for('annotate'))



@app.route("/logout")
def logout():
    #blob = flask.request.cookies
    blob = flask.request.environ
    
    sessionid = flask.session.get('sessionid')
    count = flask.session.get('count')
    
    #return flask.redirect(flask.url_for('dispatch'))
    if flask.request.args.get('cmd') == "restart":
        flask.session.pop('count', None)
        flask.session.pop('sessionid', None)
        return flask.redirect(flask.url_for('start'))
    return render_template('logout.html', css=css,sessionid=sessionid)#, blob=blob)



if __name__ == '__main__':
    #app.run(host="homebrew.usc.edu", debug=True)
    app.run(host='0.0.0.0', debug=True)
