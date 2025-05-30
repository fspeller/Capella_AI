from pymongo import MongoClient
import requests
from pymongo.server_api import ServerApi
from surprise import SVD, dump
from surprise import Dataset
from surprise import Reader
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import keras

model = keras.models.load_model('path/to/location.keras')
uri = "mongodb+srv://smartvoy_ai_1:OghvZMS8EoiJ3A8i@cluster1.nla4l.mongodb.net/?retryWrites=true&w=majority"

# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))

try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client.Capella
# 1
collection = db.customer_data

# 2
recommendation_collection = db.menu_recommender

menu_collection = db.men


# Find the most recent document in the collection
def get_most_recent_document():
    cursor = collection.find().sort("_id", -1).limit(1)
    return next(cursor, None)


# Create a change stream on the collection
with collection.watch() as stream:
    # Iterate over the stream and process the changes
    for change in stream:
        if change["operationType"] == "insert":
            new_customer = change["fullDocument"]
            most_recent_document = get_most_recent_document()
            if most_recent_document:
                # Prepare the data for the API call
                customer_id = most_recent_document["Order ID"]
                reviews = most_recent_document["'Review Sentiment'"]
                drink = most_recent_document['Drink order information']
                food = most_recent_document['Menu order information']

                food_recommendations = []
                drink_recommendations = []

                # Retrieve a list of menu items not reviewed by the customer
                menu_items = menu_collection[input].unique()
                reviewed_menu_items = collection[menu_collection['Order ID'] == customer_id][input].values
                unreviewed_menu_items = set(menu_items) - set(reviewed_menu_items)

                # Load Trained Models
                food_model = dump.load('food_recommender.sav')
                drink_model = dump.load('drink_recommender.sav')
                for menu_item in unreviewed_menu_items:
                    rating = model.predict(customer_id, menu_item).est
                    food_rating = food_model.predict(customer_id, drink).est
                    food_recommendations.append((menu_item, food_rating))

                    drink_rating = drink_model.predict(customer_id, drink).est
                    drink_recommendations.append((menu_item, drink_rating))

                food_recommendations.sort(key=lambda x: x[1], reverse=True)
                drink_recommendations.sort(key=lambda x: x[1], reverse=True)

                food_recommendation = food_recommendations[0][0]
                drink_recommendation = drink_recommendations[0][0]

                recommendation_collection.insert_one({"Food Recommendation": food_recommendation, "_id": id,
                                                      "Drink Recommendation": drink_recommendation})
                print(id)
