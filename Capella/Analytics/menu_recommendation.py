from surprise import SVD, dump
from surprise import Dataset
from surprise import Reader
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
import random
import openpyxl

food_model = dump.load('menu_recommender.sav')
print(food_model)
exit()

# Save the DataFrame to an Excel file
sample_df = pd.read_excel(r"C:\Users\freds\Downloads\Orders - Simulated Data.xlsx")
top_n = 1  # Replace with the desired number of recommendations
# Collaborative filtering using matrix factorization with Singular Value Decomposition (SVD)
# Define the reader
reader = Reader(rating_scale=(-1, 1))

input = 'Drink order information'

# Create a Surprise dataset
data = Dataset.load_from_df(sample_df[["Order ID", input, 'Review Sentiment']], reader)

# Build the collaborative filtering model
model = SVD()
model.fit(data.build_full_trainset())
dump.dump('menu_recommender.sav')
food_model = dump.load('activity_recommender.sav')

# Extract relevant features
features = [input, 'Convo Keywords', 'Review Keywords']
train_features = sample_df[features]

# Concatenate and preprocess text features
text_data = train_features[input] + ' ' + str(train_features['Convo Keywords']) + ' ' + train_features[
    'Review Keywords']
text_data = text_data.apply(lambda x: str(x).lower())

# Apply TF-IDF vectorization
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(text_data)

# Calculate cosine similarity between menu items
cosine_similarities = cosine_similarity(tfidf_matrix, tfidf_matrix)

for index, row in sample_df.iterrows():
    # Get recommendations for a specific customer
    customer_id = sample_df.loc[index, "Order ID"]  # Replace with the desired customer ID
    menu_recommendations = []

    # Retrieve a list of menu items not reviewed by the customer
    menu_items = sample_df[input].unique()
    reviewed_menu_items = sample_df[sample_df['Order ID'] == customer_id][input].values
    unreviewed_menu_items = set(menu_items) - set(reviewed_menu_items)

    # Predict ratings for unreviewed menu items and sort them in descending order
    for menu_item in unreviewed_menu_items:
        rating = model.predict(customer_id, menu_item).est
        menu_recommendations.append((menu_item, rating))

    menu_recommendations.sort(key=lambda x: x[1], reverse=True)

    print("matrix factorization with Singular Value Decomposition ")
    # Print the recommended menu items

    for recommendation in menu_recommendations[:1]:
        choice = recommendation[0]
        sample_df.loc[index, input + 'Collaborative filtering Recommendation'] = choice

    # Get recommendations for a specific menu item
    menu_item_index = index  # Replace with the desired menu item index
    menu_recommendations = []

    # Calculate similarity scores for all menu items
    similarities = cosine_similarities[menu_item_index]
    similar_items_indices = similarities.argsort()[::-1][1:]

    # Get the top N similar menu items
    for index in similar_items_indices[:top_n]:
        menu_recommendations.append((train_features.iloc[index][input], similarities[index]))

    # Print the recommended menu items'Food order information'
    print("TF-IDF and cosine similarity")
    for recommendation in menu_recommendations[:2]:
        opt1 = recommendation[0]
        v = sample_df.loc[index, input]
        if opt1 == v:
            pass
        else:
            sample_df.loc[index, input + 'Content-based filtering Recommendation'] = opt1

activities = pd.read_excel(r"C:\Users\freds\Downloads\Spa - Simulated Data.xlsx")
activities_list = activities['Order ID'].values.tolist()
activities_list.append('')
spa = pd.read_excel(r"C:\Users\freds\Downloads\Activity - Simulated Data.xlsx")
spa_list = spa['Order ID'].values.tolist()
spa_list.append('')

# Generate simulated data
simulated_data = []
for i in range(1000):
    sample_df.loc[i, 'Spa Order ID'] = random.choice(spa_list)
    sample_df.loc[i, 'Activities Order ID'] = random.choice(activities_list)

sample_df.to_excel(r"C:\Users\freds\Downloads\Orders - Simulated Data.xlsx", index=False)
