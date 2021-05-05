"""
    Demo written by James Kunstle for CS411.
    Demonstrating RESTful interface in Flask.
"""

from flask import Flask, request 
import geopy.distance
from flask_restful import Api, Resource, reqparse

import pymongo
from pymongo import MongoClient

db_loc = "mongodb+srv://jameskunstle:1701@cluster0.xsq4i.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"

cluster = MongoClient( db_loc )
db = cluster["safety_app"]
collection = db["users"]

app = Flask( __name__ )
api = Api( app )

class Users( Resource ):
    def get( self, user_id ):

        """
            if user ID in db, return json string associated with user. 
            otherwise, return null db string to confirm that the user has to enter their credentials
            to be added to the database

        """

        count_id = collection.count_documents({"_id": user_id })
        if( count_id == 0 ):
            return { "user_id": user_id, "name": "none", "birthday": "none", "home_address": "none" }
        else:
            return collection.find_one( {"_id": user_id } )

    def post( self, user_id ):

        count_id = collection.count_documents({"_id": user_id })
        if( count_id > 0 ):
            # should update the entry with new information instead of just returning 
            return collection.find_one( {"_id": user_id } )
    
        name = request.form["name"]
        street = request.form["street"]
        city = request.form["city"]
        state = request.form["state"]
        zipcode = request.form["zipcode"]
        phone_number = request.form["phone_number"]
        pin = request.form["pin"]

        user_dict = { "_id": user_id,
                        "name": name, 
                        "street": street,
                        "city": city,
                        "state": state,
                        "zipcode": zipcode,
                        "phone_number": phone_number,
                        "pin": pin }

        collection.insert_one( user_dict )
        return collection.find_one( {"_id": user_id } )

api.add_resource( Users, "/users/<int:user_id>/" )

if __name__ == "__main__":
	app.run( port=5001, debug=True )
