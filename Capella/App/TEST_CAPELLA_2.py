# Library imports
import openai
import os
from flask import Flask, jsonify, request, render_template, redirect, url_for, session, abort
from flask_cors import CORS
from datetime import datetime
import openai
from flask import request
from process_input_updated import process_input

openai.api_key = "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"

# print("Current working directory:", os.getcwd())
# print("Absolute path to templates:", os.path.abspath("templates"))

templates_dir = '../templates'  # Using a relative path to the templates directory.
# print("files:",os.listdir(templates_dir))

API_SECRET_KEY = "FF19BE3B6DD1E15F9DFB4EABB5C4B"
app = Flask(__name__, template_folder=templates_dir)
app.config["SECRET_KEY"] = "FF19BE3B6DD1E15F9DFB4EABB5C4B"
verification_codes = {}
CORS(app)

users = [
    {"last_name": "Roldan", "room_number": "512"},
    {"last_name": "Smith", "room_number": "101"},
    {"last_name": "Johnson", "room_number": "202"},
    {"last_name": "Speller", "room_number": "222"},
]


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Process the login form data
        last_name = request.form.get('last_name')
        room_number = request.form.get('room_number')
        dietary_restrictions = request.form.get('dietary_restrictions')
        # Validate the login data
        if any(user["last_name"] == last_name and user["room_number"] == room_number for user in users):
            # Redirect to the chat page after successful login
            session['last_name'] = last_name
            session['room_number'] = room_number
            session['dietary_restrictions'] = dietary_restrictions
            return redirect(url_for('chat', last_name=last_name, room_number=room_number,
                                    dietary_restrictions=dietary_restrictions))
        else:
            # Return a message to the user about unsuccessful login
            return "Invalid last name or room number. Please try again."

    return render_template('login.html')


@app.route('/chat', methods=['GET', 'POST'])
def chat():
    if 'user' not in session:
        return redirect(url_for('home'))
    last_name = request.args.get('last_name', session.get('user'))
    room_number = request.args.get('room_number')
    dietary_restrictions = request.args.get('dietary_restrictions')

    if request.method == 'POST':
        # RETRIEVING EVERYTHING FROM THE HTML
        text_input = request.form.get('text_input') if request.method == 'POST' else None
        request_method = request.method
        button_text = request.form.get('button_text') if request.method == 'POST' else None
        chat_history = request.form.get('history') if request.method == 'POST' else ''
        ip = request.form.get('ip') if request.method == 'POST' else ''
        result_id = request.form.get('_id') if request.method == 'POST' and request.form.get(
            '_id') else '6492e8adff8cb061fb55580c'

        # CREATES THE JSON BASED ON THE TEXT INPUT SUBMITTED BY CUSTOMER
        response = process_input(text_input, request_method, button_text, chat_history, ip, result_id)

        # THIS RETRIEVES THE VARIABLE FROM THE PROCESSED INPUT
        chat_history = response.get('new_history', chat_history)
        chatgpt_output = response.get('chatgpt_output')
        result_id = response.get('_id', result_id)
        ip = response.get('ip', ip)
        confirmation = 'N'
        if confirmation == 'Y':
            print('Confirmation')
            return render_template(
                'confirmation.html',
                last_name=last_name, room_number=room_number, dietary_restrictions=dietary_restrictions,
                chat_history=chat_history, ip=ip, result_id=result_id, text_input=text_input,
                chatgpt_output=chatgpt_output)

        return render_template(
            'chat_copy.html',
            last_name=last_name, room_number=room_number, dietary_restrictions=dietary_restrictions,
            chat_history=chat_history, ip=ip, result_id=result_id, text_input=text_input, chatgpt_output=chatgpt_output
        )
    return render_template(
        'chat.html',
        last_name=last_name, room_number=room_number, dietary_restrictions=dietary_restrictions
    )


@app.route('/api/chatbot/capella', methods=['GET', 'POST'])
def chatbot_api():
    print("API Called")
    # Check for the presence of the secret key in the request headers
    request_secret_key = request.headers.get('X-API-KEY')

    # If the secret key is missing or incorrect, return a 401 Unauthorized response
    if not request_secret_key or request_secret_key != API_SECRET_KEY:
        abort(401)

    data = request.get_json()
    print("Request JSON data:", data)
    text_input = data.get('text_input', None)
    request_method = data.get('request_method')
    button_text = data.get('button_text')
    chat_history = data.get('chat_history')
    ip = data.get('ip')
    result_id = data.get('_id') if request.method == 'POST' and data.get('_id') else '6492e8adff8cb061fb55580c'
    response = process_input(text_input, request_method, button_text, chat_history, ip, result_id)
    chat_history_html_formatted = response['response']
    chat_history = response.get('new_history', chat_history)
    chatgpt_output = response['chatgpt_output']
    chat_history += f'>{response}'
    return jsonify({
        'response': response,
        'new_history': chat_history_html_formatted,
        'chatgpt_output': chatgpt_output,
    })


@app.route('/conversation', methods=['GET', 'POST'])
def conversation_api():
    print('Conversation API')
    return jsonify()


if __name__ == '__main__':
    app.run(debug=True)
