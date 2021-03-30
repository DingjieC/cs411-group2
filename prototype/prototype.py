from flask import Flask, redirect, url_for, render_template, request
import geopy.distance
import json
import urllib.request
import urllib
import requests
from math import log10, floor

app = Flask( __name__ )
WARREN_LAT = 42.349380
WARREN_LON = -71.104020
url = 'https://data.boston.gov/api/3/action/datastore_search?resource_id=ba5ed0e2-e901-438c-b2e0-4acfc3c452b9&limit=100'

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        term = request.form["srchyear"]
        print(term)
        location = request.form["location"]
        print(location)
        radius = request.form["radius"]	
        print(radius)
        return redirect( url_for( "display_api", input_term=term , input_location = location, input_radius=radius) )
    else:
        return render_template( "index.html" )


"""
    TODO:

    For some hard-coded address, search for all 
    crimes of a specific type, within the last 
    5 days, within some radius of the current location.

    Address should be hard-coded for the moment,
    Crime-type should be a drop-down,
    Radius should be numerical and in Miles.
"""
@app.route( "/form_<input_term>_<input_location>_<input_radius>/" )
def display_api( input_term , input_location, input_radius):
    """
        reference:
        https://stackoverflow.com/questions/3410976/how-to-round-a-number-to-significant-figures-in-python
    """

    def round_sig(x, sig=2):
            return round(x, sig-int(floor(log10(abs(x))))-1)
    
    # update the API call to accommodate input streetname
    search_url = url + f"&q={input_term}"
    print( search_url )


    display = 20
    events = []
    geo_url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(input_location) +'?format=json'
    response = requests.get(geo_url).json()
    lat = response[0]["lat"]
    lon = response[0]["lon"]
    print(lat + " " + lon)

    event_string = f"<h1>{input_term}: Crime near {input_location} ({input_radius} mile radius)</h1>"
    
    #shows at most 20 of the crimes that happened in the submitted year.
    while( display > 0 ):


        # fetch the JSON object from the api, including all of the values
        # that have the string in them.
        fileobj = urllib.request.urlopen( search_url )
        response_dict = json.loads( fileobj.read() )

        # get event type and location of events that occurred within a mile if the event happened
        # on a Monday
        records = response_dict["result"]
        records = records["records"]
        for record in records:
            events += [ ( record["INCIDENT_TYPE_DESCRIPTION"], record["Location"] ) ]

        
        print( "Number of Events ", len(events) )
        if( len(events) == 0 ):
            break

        for kind, loc in events:

            loc = loc.split(',')
            loc[0] = loc[0][1:]
            loc[1] = loc[1][:-1]

            loc_lat = float( loc[0] )
            loc_lon = float( loc[-1] )


            dist = geopy.distance.distance( ( loc_lat, loc_lon ) , ( lat, lon ) ).miles
            dist = round_sig( dist, sig=3 )

            input_radius = int(input_radius)

            if dist < input_radius:

                display = display - 1
                if( display <= 0 ):
                    break

                event = f"<p> { kind.lower().capitalize() } : {dist} miles away. </p>"
                event_string += event
                print( "events remaining:", display )
                print( "EVENT_STRING", event )
            
        if( display > 0 ):
            search_url = "https://data.boston.gov" + ((response_dict["result"])["_links"])["next"] 
            print( "SEARCH URL:", search_url )
        else:
            break

    return event_string	
    

if __name__ == "__main__":

#	print( geopy.distance.distance( ( WARREN_LAT, WARREN_LON) , ( 42.352240, -71.127520) ).miles )
    app.run( debug=True )
