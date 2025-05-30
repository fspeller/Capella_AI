import tiktoken
import psutil
import re
import string
import openai
from flask import request, json, session
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
import os
from multiprocessing import Pool
from config import *
from heroku_log import *

cost = 0


def Convert(string):
    li = list(string.split(">"))
    return li


def find_between(s, first, last):
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        x = "{" + s[start:end] + "}"
        return x
    except ValueError:
        return ""


def num_tokens_from_string(string, encoding_model):
    num_tokens = 0

    if encoding_model == "gpt-3.5-turbo":
        encoding = tiktoken.encoding_for_model(encoding_model)
        num_tokens = 0.002 * len(encoding.encode(string)) / 1000

    elif encoding_model == "text-davinci-002":
        encoding = tiktoken.encoding_for_model(encoding_model)
        num_tokens = 0.02 * len(encoding.encode(string)) / 1000
    return num_tokens


def identify_language(text):
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=f"What language is the following text in: '{text}'?",
        temperature=0.5,
        max_tokens=20,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )
    return response.choices[0].text.strip()


def content_filter(conversation, language):
    filter_prompt = f"""AI is a hotel concierge expert and content moderator that understands all language. 
    AI uses the following criteria to categorize conversations into three distinct categories: "General" ,"Dining", "Dining Order Completion" ,"Hotel","Dining Confirmation",
    "Spa", "Spa Confirmation" and "Not Recommended".
    
    The criteria for the General category is, a conversation that is related to the company SmartVoy and not ordering food at the Capella Restaurant or the 
    Capella Hotel in general.
    
    The criteria for the Hotel category is, a conversation that is related to Capella Hotel and its rooms, services.

    The criteria for the Spa category is, a conversation that is related to spa located in the capella hotel and it's services, and   

    The criteria for the Dining category is, a conversation that is related to the restaurant or to ordering food items from the restaurant or 
    is related questions about the restaurant menu and/or menu items.
    
    The criteria for the Dining Order Completion category is, a conversation that related to finalizing an food order for a customer and all of the
    customer is ready to pay for their food and send the order to the kitchen.
    
    Please respond to requests for conversation category, with only the designated category

    """

    lst = [{"role": "system", "content": filter_prompt},
           {"role": "user",
            "content": f"""Categorize this ChatGPT conversation: {conversation} , into either "General" ,"Dining", "Hotel","Spa" and "Not Recommended" based on the criteria provided in the prompt.What is the category ?"""}]

    # Create ChatCompletion request
    output = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=lst,  # Use lst instead of conversation
        temperature=0.7,  # Adjust temperature for more focused output
        max_tokens=200,  # Limit response length
    )

    answer = output.choices[0].message['content'].strip().lower()
    return answer


def parse_user_info(user_input):
    # Initialize an empty dictionary
    user_info = {}

    # Generate a prompt asking for the user's information
    prompt = f"Based on this text {user_input}Please provide the following information:\n1. Your room number\n2. Your name\n3. Any dietary restrictions"

    # Use the OpenAI API to generate a response
    output = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        temperature=0.5,
        max_tokens=100
    )
    generated_response = output.choices[0].text.strip()

    # Parse the generated response
    response_lines = generated_response.split("\n")
    for line in response_lines:
        if ": " in line:
            key, value = line.split(": ", 1)
            user_info[key.strip()] = value.strip()

    # Return the dictionary
    return user_info


# Define a global variable to store the user's information
user_info_data = {}


def chatcompletion(user_input, conversation, dietary_restrictions, last_name, room_number):
    # Identify the language of the user input
    language = identify_language(user_input)
    global cost

    # Update the system message
    system_message = {
        "role": "system",
        "content": (
            "As a virtual concierge at our esteemed establishment, your mission is to provide exceptional service and cater to our guests' needs with the utmost professionalism. "
            f"Your role encompasses a deep understanding of our hotel's services, amenities, and offerings, as well as comprehensive knowledge about the vibrant city of {city} and its many attractions. "
            f"Address each guest, Mr. or Ms., with the appropriate title to maintain a formal tone throughout the conversation. "
            f"Your primary objective is to offer accurate and informative responses, ensuring our guests, like Mr./Ms. {last_name}, have a memorable and enriching experience during their stay in room {room_number} with us. "
            "Please utilize your expertise to answer inquiries regarding accommodations, dining options, wellness facilities, events, and any other relevant aspects of our establishment. "
            f"Additionally, feel free to provide insights into the local culture, cuisine, weather, and notable points of interest within {city}. "
            "Adopting a courteous and professional approach, your aim is to exceed our guests' expectations and contribute to their overall satisfaction. "
            "Thank you for your dedication and commitment to delivering exceptional service as our virtual concierge."
        )
    }

    conversation.insert(0, system_message)
    print(system_message)
    print("Get Answer from content filter")
    answer = content_filter(conversation, language)
    print("Content Filter Response:", answer)
    answer = answer.translate(str.maketrans('', '', string.punctuation))
    answer_words = set(answer.lower().split())
    cost += num_tokens_from_string(answer, "gpt-3.5-turbo")

    hotel_category = ["Hotels", "rooms", "villas", "manors", "suites", "General", "general"]
    dining_category = ["Restaurant", "dining", "Menu"]
    dining_completion_category = ["Dining Order Completion", "Food Order Completion", "Dining Order Finalization"]
    spa_category = ["Spa", "spa.", "Massage", "Treatments", "relaxation", "\"spa\"", "spa"]
    restaurant_availability_ = ["restaurant", "book", "reserve"]
    not_recommended = ["No", "Would not recommend", "No criteria"]

    if any(word in answer_words for word in hotel_category):
        conversation[1] = {"role": "system",
                           "content": prompt}  # Proper way to do it - modify the rest and revert prompt
        # conversation[1] = prompt
        print("Hotel Prompt")
        # Create ChatCompletion request
        output = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=conversation,
            temperature=0.7,  # Adjust temperature for more focused output
            max_tokens=200,  # Limit response length
        )
        chatgpt_output = output['choices'][0]['message']['content']
        confirmation = 'N'
    elif any(word in answer_words for word in dining_category):
        print('Dining Prompt')
        ird_prompt = generate_prompt([dietary_restrictions, last_name, room_number])
        # NEED TO ADD THE UPDATE PROMPT HERE
        conversation[1] = {"role": "system", "content": ird_prompt}
        print(conversation)
        # Create ChatCompletion request
        output = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=conversation,
            temperature=0.7,  # Adjust temperature for more focused output
            max_tokens=200,  # Limit response length
        )
        chatgpt_output = output['choices'][0]['message']['content']
        confirmation = 'N'
        # Save the user's information in the global variable

    elif any(word in answer_words for word in spa_category):
        conversation[1] = {"role": "system", "content": spa_prompt}
        print("Spa Prompt")
        # Create ChatCompletion request
        output = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=conversation,
            temperature=0.7,  # Adjust temperature for more focused output
            max_tokens=200,  # Limit response length
        )
        chatgpt_output = output['choices'][0]['message']['content']
        confirmation = 'N'
    elif any(word in answer_words for word in restaurant_availability_):
        conversation[1] = {"role": "system", "content": restaurant_availability_time}
        print("Restaurant Prompt")
        # Create ChatCompletion request
        output = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k-0613",
            messages=conversation,
            temperature=0.7,  # Adjust temperature for more focused output
            max_tokens=200,  # Limit response length
        )
        chatgpt_output = output['choices'][0]['message']['content']
        confirmation = 'N'
    elif any(word in answer_words for word in dining_completion_category):
        confirmation = 'Y'
    else:
        # any(word in answer_words for word in not_recommended)
        chatgpt_output = decline_message
        confirmation = 'N'
    return [chatgpt_output, confirmation]


def inner_chatcompletion(user_input, conversation):
    # Create ChatCompletion request
    output = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k-0613",
        messages=conversation,
        temperature=0.7,  # Adjust temperature for more focused output
        max_tokens=1000,  # Limit response length
    )
    chatgpt_output = output['choices'][0]['message']['content']
    return chatgpt_output


def is_valid_excel_file(path):
    return os.path.isfile(path) and path.endswith('.xlsx')


def is_file_open(path):
    for proc in psutil.process_iter(['pid', 'open_files']):
        if path in (f.path for f in proc.info['open_files'] or ()):
            return True
    return False


def calculate_total(df, order_info):
    # Initialize the total to 0
    total = 0

    # Check if order_info is a dictionary
    if isinstance(order_info, dict):
        # Loop over all items in the order
        for item, quantity in order_info.items():
            # Check if the item is in the DataFrame
            if item in df["Meal"].values:
                # If it is, add the price times quantity to the total
                price = df.loc[df["Meal"] == item, "Price"].values[0]
                total += price * quantity
    # If order_info is a list
    elif isinstance(order_info, list):
        # Loop over all items in the order
        for item in order_info:
            # Check if the item is in the DataFrame
            if item in df["Meal"].values:
                # If it is, add its price to the total
                price = df.loc[df["Meal"] == item, "Price"].values[0]
                total += price
    # If order_info is not a dictionary or list, treat it as a string
    else:
        # Split the string into items
        items = order_info.split(', ')
        for item in items:
            # Extract the food name and quantity if provided
            match = re.match(r'^(.*?)\s*\((\d+)\)$', item)
            if match:
                food_name, quantity = match.groups()
                quantity = int(quantity)
            else:
                food_name = item.strip()
                quantity = 1
            # Check if the food name is in the DataFrame
            if food_name in df["Meal"].values:
                # If it is, add its price times quantity to the total
                price = df.loc[df["Meal"] == food_name, "Price"].values[0]
                total += price * quantity

    return total


path = r"C:\Users\Luis Marcelo Roldan\Desktop\AAAA\Desenrolei_python_code\Working files\final\AICODE_APP\AITRIP\New folder\Improvements\Github\Smartvoy_Dev_Master-Capella_Example\Capella_denji_flask\Finals_versions\orders.xlsx"


def process_input(text_input=None, request_method=None, button_text=None, chat_history=None, ip=None, result_id=None):
    global cost
    chat_history_html_formatted = ''
    chatgpt_output = None
    chat_output_improved = None
    orders = pd.DataFrame()

    # Retrieve the information from the session
    last_name = session.get('last_name')
    room_number = session.get('room_number')
    dietary_restrictions = session.get('dietary_restrictions')

    if request_method == 'POST' or text_input:

        # Use text_input parameter directly
        user_input = text_input

        if request.headers.get('Content-Type') == 'application/json':
            data = request.get_json()
            user_input = data.get('text_input')
        else:
            user_input = request.form.get('text_input')

        new_log = retrieve_logs(log_url, headers, payload)
        ip = "192.168.15.25"  # next(item['ip_address'] for item in new_log for key, value in item.items() if key == 'ip_address')
        # default_location = next(item['City'] for item in new_log for key, value in item.items() if key == 'City')
        # hostname = next(item['Hostname'] for item in new_log for key, value in item.items() if key == 'Hostname')
        # ird_prompt = generate_prompt()
        conversation = [{"role": "system", "content": prompt}]
        inner_conversation = [{"role": "system", "content": prompt}]
        try:
            conv_history = Convert(chat_history)
            del conv_history[0]
            count = 0
            for x in conv_history:
                count = count + 1
                cost += num_tokens_from_string(x, "gpt-3.5-turbo")
                if cost > 10.05:
                    exit()
                if (count % 2) != 0:
                    inner_conversation.append({"role": "user", "content": x})
                    conversation.append({"role": "user", "content": x})
                else:
                    conversation.append({"role": "assistant", "content": x})
                    inner_conversation.append({"role": "assistant", "content": x})

            print("CURRENT COST: ", cost)
        except:
            pass

        if button_text == 'Clear Chat History':
            chat_history = ''
            chat_history_html_formatted = ''
            return {'response': chat_history_html_formatted}

        elif button_text == 'submit':
            # Initialize multiprocessing Pool
            inner_conversation.append({"role": "user", "content": "Please provide the customer python dictionary"})
            conversation.append({"role": "user", "content": user_input})  # FORMAT TO ADD THE PROMPT

            # New Convo
            if chat_history == " ":
                print('New Convo')
                with Pool(processes=2) as pool:
                    # Prepare arguments for the functions
                    chatcompletion_args = (user_input, conversation, dietary_restrictions, last_name, room_number)
                    inner_chatcompletion_args = ("Please provide the customer python dictionary", inner_conversation)

                    # Run the functions in parallel
                    chatcompletion_result = pool.apply_async(chatcompletion, args=chatcompletion_args)
                    inner_chatcompletion_result = pool.apply_async(inner_chatcompletion, args=inner_chatcompletion_args)
                    inner_convo_chatgpt_output = inner_chatcompletion_result.get()

                    try:
                        inner_convo_chatgpt_output = find_between(inner_convo_chatgpt_output, "{", "}")
                        inner_convo_chatgpt_output = json.loads(inner_convo_chatgpt_output)
                        # print("THIS IS THE INNER MONOLOGUE: ", inner_convo_chatgpt_output)

                        try:
                            # Set up MongoDB connection using environment variables
                            uri = "mongodb+srv://smartvoy_ai_1:OghvZMS8EoiJ3A8i@cluster1.nla4l.mongodb.net/?retryWrites=true&w=majority"
                            # Create a new client and connect to the server
                            client = MongoClient(uri, server_api=ServerApi('1'))
                            # Send a ping to confirm a successful connection
                            try:
                                client.admin.command('ping')
                            except Exception as e:
                                print(e)

                            db = client.Capella
                            collection = db.customer_data

                            # inner_convo_chatgpt_output['log'] = new_log
                            inner_convo_chatgpt_output['cost'] = cost
                            inner_convo_chatgpt_output['ip'] = ip
                            inner_convo_chatgpt_output['chat history'] = conversation
                            inner_convo_chatgpt_output['Inner Monologue'] = inner_conversation

                            result = collection.insert_one(inner_convo_chatgpt_output)
                            result_id = result.inserted_id
                        except Exception as e:
                            print(e)
                        finally:
                            client.close()
                    except Exception as e:
                        print(e)
                    # Active Conversation
                    if user_input is not None:
                        chat_history += ">" + user_input
                    else:
                        # Handle the case where user_input is None
                        chat_history += "> "

                    if user_input is not None:
                        chatgpt_lst = chatcompletion_result.get()
                        chatgpt_output = chatgpt_lst[0]
                        confirmation = chatgpt_lst[1]
                        conversation.append({"role": "assistant", "content": chatgpt_output})
                        chat_history += ">" + chatgpt_output

            # If continuing Conversation
            else:
                print("Continuing Conversation")
                with Pool(processes=2) as pool:
                    # Prepare arguments for the functions
                    # Calculate the total for the order

                    # Set up MongoDB connection using environment variables
                    uri = "mongodb+srv://smartvoy_ai_1:OghvZMS8EoiJ3A8i@cluster1.nla4l.mongodb.net/?retryWrites=true&w=majority"
                    # Create a new client and connect to the server
                    client = MongoClient(uri, server_api=ServerApi('1'))
                    # Send a ping to confirm a successful connection
                    try:
                        client.admin.command('ping')
                        db = client.Capella
                        prompt_collection = db.temp_prompt

                        # Perform the query to find the document
                        prompt_document = prompt_collection.find_one(ObjectId(result_id))

                        # Check if a document was found with the specified "id"
                        if prompt_document:
                            updated_prompt = prompt_document.get("Prompt")

                            # Check if there is a prompt update available
                            if updated_prompt != '':
                                conversation[0] = updated_prompt
                            else:
                                pass
                            # print("Prompt value:", updated_prompt)
                        else:
                            print("No document found with the specified id.")

                        # Close the MongoDB connection
                        # print("Closing MongoDB connection...")
                        client.close()
                    except Exception as e:
                        print(e)
                    chatcompletion_args = (user_input, conversation, dietary_restrictions, last_name, room_number)
                    inner_chatcompletion_args = ("Please provide the customer python dictionary", inner_conversation)

                    # Run the functions in parallel
                    chatcompletion_result = pool.apply_async(chatcompletion, args=chatcompletion_args)
                    inner_chatcompletion_result = pool.apply_async(inner_chatcompletion, args=inner_chatcompletion_args)
                    inner_convo_chatgpt_output = inner_chatcompletion_result.get()
                    try:
                        # Inner Monologue to parse information
                        # print("Parse Dict from Results")
                        inner_convo_chatgpt_output = find_between(inner_convo_chatgpt_output, "{", "}")
                        if inner_convo_chatgpt_output:
                            if isinstance(inner_convo_chatgpt_output, str):
                                x = 0
                                for c in inner_convo_chatgpt_output:
                                    if c == "{":
                                        x += 1
                                    elif c == "}":
                                        x -= 1
                                i = 0
                                while i < x:
                                    inner_convo_chatgpt_output += "}"
                                    i += 1

                        # Update Prompt
                        print("THIS IS THE INNER MONOLOGUE: ", inner_convo_chatgpt_output)
                        try:
                            # Set up MongoDB connection using environment variables
                            uri = "mongodb+srv://smartvoy_ai_1:OghvZMS8EoiJ3A8i@cluster1.nla4l.mongodb.net/?retryWrites=true&w=majority"
                            # Create a new client and connect to the server
                            client = MongoClient(uri, server_api=ServerApi('1'))
                            # Send a ping to confirm a successful connection
                            try:
                                client.admin.command('ping')
                                # print("Pinged your deployment. You successfully connected to MongoDB!")
                            except Exception as e:
                                print(e)
                            db = client.Capella
                            collection = db.ird_menu
                            inner_convo_chatgpt_output = json.loads(inner_convo_chatgpt_output)

                            menu = load_mongodb_into_dataframe(db, collection)
                            total = calculate_total(menu, inner_convo_chatgpt_output["Food order information"])
                            client.close()
                            # Add the total to the conversation
                            conversation = [{"role": "assistant", "content": f"The total for your order is {total}."}]

                            print("THIS IS THE INNER MONOLOGUE Food Order Cost: ", total)
                        except Exception as e:
                            print(e)

                        orders = pd.DataFrame([inner_convo_chatgpt_output])

                        print(confirm)

                        try:
                            # Set up MongoDB connection using environment variables
                            uri = "mongodb+srv://smartvoy_ai_1:OghvZMS8EoiJ3A8i@cluster1.nla4l.mongodb.net/?retryWrites=true&w=majority"
                            # Create a new client and connect to the server
                            client = MongoClient(uri, server_api=ServerApi('1'))
                            # Send a ping to confirm a successful connection
                            try:
                                client.admin.command('ping')
                                # print("Pinged your deployment. You successfully connected to MongoDB!")
                            except Exception as e:
                                print(e)

                            db = client.Capella
                            # 1
                            collection = db.customer_data

                            # inner_convo_chatgpt_output['log'] = new_log
                            inner_convo_chatgpt_output['cost'] = cost
                            inner_convo_chatgpt_output['ip'] = ip
                            inner_convo_chatgpt_output['chat history'] = conversation
                            inner_convo_chatgpt_output['Inner Monologue'] = inner_conversation
                            # Define the filter to match the document with the given ObjectId
                            c_filter = {"_id": ObjectId(result_id)}

                            # Define the update operation with the new dictionary
                            update = {"$set": inner_convo_chatgpt_output}

                            # Perform the update operation
                            inner_document = collection.update_one(c_filter, update)

                            # Check if the update was successful
                            if inner_document.modified_count > 0:
                                print("Document updated successfully.")
                            else:
                                print("No document found with the specified ObjectId.")

                        finally:
                            client.close()

                    except Exception as e:
                        print(e)

                    # Active Conversation
                    if user_input is not None:
                        chat_history += ">" + user_input
                    else:
                        # Handle the case where user_input is None
                        chat_history += "> "

                    if user_input is not None:
                        chatgpt_lst = chatcompletion_result.get()
                        chatgpt_output = chatgpt_lst[0]
                        confirmation = chatgpt_lst[1]
                        # chat_output_improved = improve_response(chatgpt_output)
                        # print(f"This is the improved response: {chatgpt_output}")
                        conversation.append({"role": "assistant", "content": chatgpt_output})
                        chat_history += ">" + chatgpt_output

    return {'new_history': chat_history or '',
            'chatgpt_output': chatgpt_output or '', 'ip': ip or '', '_id': result_id or '', 'cost': cost or '',
            'confirmation': confirmation or ''}
