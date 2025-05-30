from surprise import SVD, Dataset, Reader, dump
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd


# Save the DataFrame to an Excel file
sample_df = pd.read_excel(r"C:\Users\freds\Downloads\Activity - Simulated Data.xlsx")
top_n = 1  # Replace with the desired number of recommendations
# Collaborative filtering using matrix factorization with Singular Value Decomposition (SVD)
# Define the reader
reader = Reader(rating_scale=(-1, 1))

# Create a Surprise dataset
data = Dataset.load_from_df(sample_df[["Order ID", 'Activity or Restaurant', 'Review Sentiment']], reader)

# Build the collaborative filtering model
model = SVD()
model.fit(data.build_full_trainset())
dump.dump('activity_recommender.sav')

# Extract relevant features
features = ['Activity or Restaurant', 'Convo Keywords',  'Review Keywords']
train_features = sample_df[features]

# Concatenate and preprocess text features
text_data = train_features['Activity or Restaurant'] + ' ' + str(train_features['Convo Keywords']) + ' ' + train_features['Review Keywords']
text_data = text_data.apply(lambda x : str(x).lower())

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
    menu_items = sample_df['Activity or Restaurant'].unique()
    reviewed_menu_items = sample_df[sample_df['Order ID'] == customer_id]['Activity or Restaurant'].values
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
        sample_df.loc[index, 'Collaborative filtering Recommendation'] = choice


    # Get recommendations for a specific menu item
    menu_item_index = index  # Replace with the desired menu item index
    menu_recommendations = []

    # Calculate similarity scores for all menu items
    similarities = cosine_similarities[menu_item_index]
    similar_items_indices = similarities.argsort()[::-1][1:]

    # Get the top N similar menu items
    for index in similar_items_indices[:top_n]:
        menu_recommendations.append((train_features.iloc[index]['Activity or Restaurant'], similarities[index]))

    # Print the recommended menu items'Food order information'
    print("TF-IDF and cosine similarity")
    for recommendation in menu_recommendations[:2]:
        opt1 = recommendation[0]
        v = sample_df.loc[index, 'Content-based filtering Recommendation']
        if opt1 == v:
            pass
        else:
            sample_df.loc[index, 'Content-based filtering Recommendation'] = opt1


sample_df.to_excel(r"C:\Users\freds\Downloads\Activity - Simulated Data.xlsx", index=False)