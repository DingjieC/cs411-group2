import os
from flask import Flask, redirect, url_for, render_template, request

from flask_dance.contrib.facebook import make_facebook_blueprint, facebook
import requests

import pymongo
from pymongo import MongoClient

import gmplot
import os
import geocoder
import datetime
from datetime import timedelta
import math
import json
from operator import itemgetter

BASE = "http://127.0.0.1:5001" #address of the backend server, base

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "supersekrit")
app.config["FACEBOOK_OAUTH_CLIENT_ID"] = 2977753549121894
app.config["FACEBOOK_OAUTH_CLIENT_SECRET"] = "4885f076cf6a592e58810c6967d2a1ed"
app.config["OAUTHLIB_INSECURE_TRANSPORT"] = "true"
facebook_bp = make_facebook_blueprint()
app.register_blueprint(facebook_bp, url_prefix="/login")

api_key = "AIzaSyApeNoZj_DRHq9mCZ8aEnkZx1IHqpPUt_Q"

noonlighturl = "https://api-sandbox.noonlight.com/dispatch/v1/alarms"

@app.route("/", methods=["GET", "POST"])
def base_page():
    if request.method == "POST":
        return redirect( url_for( "facebook_login" ) )
    else:
        return render_template( "index.html" )

@app.route("/login/")
def facebook_login():
    
    # check if we are authorized on facebook
    if not facebook.authorized:
        return redirect(url_for("facebook.login"))
        
    resp = facebook.get("/me")
    assert resp.ok, resp.text

    # once we are authorized on facebook, get our unique user ID
    user_id = resp.json()["id"]
    #user_id = 1235354558502 #temporary ID that is not correct

    # get req to the backend- query DB for user profile
    response = requests.get( BASE + f"/users/{user_id}/" )
    response = response.json()

    # if the user is in the database, redirect us to their page
    if( response["name"] == "none" ):
        return redirect( url_for( "new_user", user_id = user_id ) ) 
    # otherwise, redirect to account creation page
    else:
        return redirect( url_for( "user_page", user_id = user_id ) )

@app.route("/new_user/<user_id>", methods=["GET", "POST"] )
def new_user( user_id ):
    if request.method == "POST":
        name = request.form["name"]
        street = request.form["street"]
        city = request.form["city"]
        state = request.form["state"]
        zipcode = request.form["zipcode"]
        phone_number = request.form["phone_number"]
        pin = request.form["pin"]

        user_dict = { "name": name, 
                        "street": street,
                        "city": city,
                        "state": state,
                        "zipcode": zipcode,
                        "phone_number": phone_number,
                        "pin": pin }
        resp = requests.post( BASE + f"/users/{user_id}/", user_dict )
        resp_j = resp.json()
        return redirect( url_for( "user_page", user_id = user_id) )
    else:
        return render_template( "new_login.html" )

@app.route("/logged_in/<user_id>", methods=["GET", "POST"])
def user_page( user_id ):
    if request.method == "POST":

        if( request.form.get("routing") == "Route to Location"):
           return redirect( url_for( "search", user_id = user_id ) )

        elif( request.form.get("emergency") == "Emergency"):
            return redirect( url_for("noonlight", user_id = user_id) )

        elif( request.form.get("crime") == "Crime Map"):
            return redirect( url_for( "crime_data", user_id = user_id ) )

        elif( request.form.get("businesses") == "Open Businesses"):
            return redirect(url_for("display_yelp_api", user_id = user_id))

        else:
            return render_template("user_page.html")
    else:
        return render_template("user_page.html")

@app.route( "/noonlight/<user_id>", methods=["GET", "POST"])
def noonlight(user_id):
    if request.method == "POST":
        resp = requests.get( BASE + f"/users/{user_id}/" )
        resp_j = resp.json()
        print(resp_j)
        city = resp_j["city"]
        name =resp_j["name"]
        phone_number = resp_j["phone_number"]
        pin =resp_j["pin"]
        state =resp_j["state"]
        street =resp_j["street"]
        zipcode =resp_j["zipcode"]
        payload = {
        "location": {"address": {
                "line1": street,
                "city": city,
                "state": state,
                "zip": zipcode
            }},
        "services": {
            "police": True,
            "fire": True,
            "medical": True,
            "other": False
        },
        "instructions": {"entry": "entry code"},
        "phone": phone_number,
        "name": name,
        "pin": pin
        }
        headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer Sig9DITLpn1eUd3Jmta5NUaMEC6qsfai"
        } 
        response2 = requests.request("POST", noonlighturl, json=payload, headers=headers)
        print(response2.text)
        i = 7
        alarmid = ""
        while response2.text[i] != ",":
            if(response2.text[i] != '"'):
                alarmid += response2.text[i]
            i+=1
        print(alarmid)
        return render_template("noonlightoptions.html", a_id = alarmid, user_id = user_id)
    else:
        return render_template("noonlight.html")

@app.route("/noonlight_alarms_create/<a_id>/<user_id>", methods=['GET', 'POST'])
def create(a_id, user_id):
    if request.method == "POST":
        name = request.form["name"]
        print(name)
        pin = request.form["pin"]
        print(pin)
        phone = request.form["phone"]
        print(phone)
        url1 = "https://api-sandbox.noonlight.com/dispatch/v1/alarms/" + a_id + "/people"
        payload = [{
        "name": name,
        "pin": pin,
        "phone": phone
        }]
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer Sig9DITLpn1eUd3Jmta5NUaMEC6qsfai"
            }
        response2 = requests.request("POST", url1, json=payload, headers=headers)
        print(response2.text)
        return render_template("noonlightoptions.html", a_id = a_id, user_id = user_id)

@app.route("/noonlight/status/<a_id>/<user_id>", methods=['GET', 'POST'])
def cancel(a_id, user_id):
    cancelurl = "https://api-sandbox.noonlight.com/dispatch/v1/alarms/" + a_id + "/status"
    payloadcancel = {"pin": "1234", 
                    "status": "CANCELED"}
    headerscancel = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Authorization": "Bearer Sig9DITLpn1eUd3Jmta5NUaMEC6qsfai"
    }
    responsecancel = requests.request("POST", cancelurl, json=payloadcancel, headers=headerscancel)
    print(responsecancel.text)
    return render_template("cancellation_page.html", a_id = a_id, user_id = user_id)

@app.route("/back_to_home/<user_id>", methods=['GET', 'POST'])
def go_to_home(user_id):
    return redirect( url_for( "user_page", user_id = user_id) )



@app.route("/map/<user_id>", methods=['GET', 'POST'])
def map(user_id):
    return render_template('map.html',user_id = user_id)


@app.route("/search/<user_id>", methods=["GET", "POST"])
def search( user_id ):
    if request.method == "POST":
        
        gmap = gmplot.GoogleMapPlotter.from_geocode('Boston University', apikey=api_key)
        ori = request.form['ori']
        
        des = request.form['des']
       # print(type(des))
      
        origin = gmplot.GoogleMapPlotter.geocode(ori, apikey=api_key)
        destination = gmplot.GoogleMapPlotter.geocode(des, apikey=api_key)
        mode =["WALKING","BICYCLING","TRANSIT","DRIVING"]
        gmap.directions(origin,destination,travel_mode=mode[0])
        
        path = os.path.abspath(os.getcwd())
        path += "/templates/"
        gmap.draw(path+'map.html')
        #redirect( url_for( "map") )
        
        return  redirect( url_for( "map",user_id = user_id) )
    else:
        return render_template('map_search.html',user_id = user_id)

yelp_base_url = 'https://api.yelp.com/v3/businesses/search?'

@app.route("/open_businesses_near_me/<user_id>", methods=['GET', 'POST'])
def display_yelp_api(user_id):
    curr_loc = geocoder.ipinfo('me')
    input_lat = str(curr_loc.latlng[0])
    input_long = str(curr_loc.latlng[1])
    input_rad_in_mi = 1
    # !Yelps input radius is in meters and must be an int. Convert miles to meters
    input_rad_in_mtr = math.floor(input_rad_in_mi * 1609.34)

    #convert floats to strings for request payload
    payload_rad = str(input_rad_in_mtr)

    # GET request params
    payload = {'latitude': input_lat, 'longitude': input_long, 'radius': input_rad_in_mtr, 'open_now': 'true'}

    # Adding API Key to request header
    headers = {'Authorization': 'Bearer 5tH0TUqZtFrYsX0Jp31k7McHUVxdnV4KEojl4uPzJZPVfMzubVRLCSmAeIMRg51AnzBxQMltAU33ATktN7i3KMV1MqeQRsHL0kfOZhsHcR1zjASbQ5CXofzAHQSPYHYx'}

    # GET request
    yelp_response = requests.get(yelp_base_url, params=payload, headers=headers)
    yelp_output = yelp_response.json()
    businesses = yelp_output["businesses"]

# parse JSON result
    businesses_list = []
    coords_list = []

    for x in range(len(businesses)):
        yelp_id = businesses[x]["id"]
        business_name = businesses[x]["name"]
        business_addr = businesses[x]["location"]["display_address"]
        
        business_coord = (businesses[x]["coordinates"]["latitude"], businesses[x]["coordinates"]["longitude"])
        coords_list.append(business_coord)
        
        business_dist = math.ceil(businesses[x]["distance"])
        
        # store as tuple, append to list
        businesses_list.append((yelp_id, business_name, business_addr, business_coord, business_dist))
        
    businesses_list.sort(key=itemgetter(4))

    api_key = "AIzaSyApeNoZj_DRHq9mCZ8aEnkZx1IHqpPUt_Q"    
    gmap = gmplot.GoogleMapPlotter(input_lat, input_long, 14, apikey=api_key)
    attractions_lats, attractions_lngs = zip(*coords_list)
    gmap.scatter(attractions_lats, attractions_lngs, color='#0B6EEF', size=15, marker=True)
    path = os.path.abspath(os.getcwd())
    path += "/templates/"
    gmap.draw(path+'businesses_map.html')

    if request.method == "POST":
        if request.form.get('visualize') == 'Map':
            return render_template('businesses_map.html')
        else:
            return render_template('businesses.html', input_lat=input_lat, input_long=input_long, input_rad_in_mi=input_rad_in_mi, businesses_list = businesses_list)
    else:
        return render_template('businesses.html', input_lat=input_lat, input_long=input_long, input_rad_in_mi=input_rad_in_mi, businesses_list = businesses_list)

@app.route("/crime_data/<user_id>", methods=['GET', 'POST'])
def crime_data( user_id ):

    REBUILD = False
    api_key = "AIzaSyApeNoZj_DRHq9mCZ8aEnkZx1IHqpPUt_Q"

    today = datetime.datetime.now()
    last_month= today - timedelta(days=7)
    
    today = today.strftime("%Y-%m-%d %H:%M:%S")
    last_month = last_month.strftime("%Y-%m-%d %H:%M:%S")
    
    myloc = geocoder.ip('me')
    myloc = myloc.latlng
    
    my_lat = myloc[0]
    my_lon = myloc[1]
    dist = "1mi"

    if( REBUILD ):
        
        BASE = f"https://api.crimeometer.com/v1/incidents/raw-data?lat={lat}&lon={lon}&distance={dist}&datetime_ini={last_month}&datetime_end={today}&page=1"
        
        response = requests.get( BASE , headers={"x-api-key": "EBYVZGzE7e3TVmvJALpRM7TLNmlKJGnm3FKlPVub"})
        response = response.json()

        with open('crimeometer_data.json', 'w') as outfile:
            json.dump(response, outfile)
    else:
        with open("crimeometer_data.json") as json_file:
            response = json.load(json_file)

    crime_list = []
    crime_coords_list = []
    
    for idx, incident in enumerate( response["incidents"] ):
        """
        if( idx < 10 ):
            print( incident["incident_offense"] )
            print( incident["incident_address"] )
            date = datetime.datetime.strptime( incident["incident_date"] , '%Y-%m-%dT%H:%M:%S.%fZ')
            print( date )
            print( incident["incident_latitude"])
            print( incident["incident_longitude"])
            print()
        """
            

        crime_type = incident["incident_offense"]
        crime_address = incident["incident_address"]
        crime_time = datetime.datetime.strptime( incident["incident_date"] , '%Y-%m-%dT%H:%M:%S.%fZ')
        crime_coords = (incident["incident_latitude"], incident["incident_longitude"])

        crime_coords_list.append( crime_coords )
        crime_list.append( (crime_type, crime_address, crime_coords, crime_time ) )

    gmap = gmplot.GoogleMapPlotter( str(my_lat), str(my_lon), 14, apikey=api_key)

    crimes_lats, crimes_lons = zip(*crime_coords_list)

    gmap.scatter( crimes_lats, crimes_lons, color='#0B6EEF', size=15, marker=True)

    path = os.path.abspath(os.getcwd())
    path += "/templates/"
    gmap.draw(path+'crime_map.html')

    if request.method == "POST":
        if( request.form.get('visualize') == 'Map' ):
            return render_template('crime_map.html')
        elif( request.form.get('navigate') == 'Home' ):
            return redirect( url_for( "user_page", user_id=user_id))
        else:
            return render_template('crimes.html', input_lat=str(my_lat), input_long=str(my_lon), input_rad_in_mi=1, crime_list = crime_list)
    else:
        return render_template('crimes.html', input_lat=str(my_lat), input_long=str(my_lon), input_rad_in_mi=1, crime_list = crime_list)

if __name__ == "__main__":
    app.run( debug=True, host="localhost", ssl_context='adhoc')
