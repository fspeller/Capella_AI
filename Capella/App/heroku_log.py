import requests
from datetime import datetime

from flask import json

log_url = "https://api.heroku.com/apps/smartvoytest/log-sessions"
payload = [
    {"dyno": "router", "lines": 1},  # Payload for the first dyno
    {"dyno": "web.1", "lines": 1}  # Payload for the second dyno
]
headers = {
    "Accept": "application/vnd.heroku+json; version=3",
    "Authorization": "Bearer 6c3a2611-3810-4e1b-9dd9-a1c5ea8757cb"  # Replace with the appropriate authentication token
}


def parse_log(log):
    # start_time = time.time()
    parsed_data = {"fwd": None, "text_input": None, "chatgpt_output": None, "timestamp": None}
    try:
        if "fwd" in log:
            fwd_index = log.index("fwd=") + 5
            parsed_data["fwd"] = log[fwd_index:].split('"')[0]

        timestamp = log.split(" ")[0]
        parsed_data["timestamp"] = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f%z")

        if "Request JSON data" in log:
            json_data = log.split("Request JSON data:")[-1].strip()
            json_data = json_data.replace("'", '"')  # Replace single quotes with double quotes
            data = json.loads(json_data)
            if "text_input" in data and data["text_input"] != "none":
                parsed_data["text_input"] = data["text_input"]
            if "chat_history" in data:
                chat_history = data["chat_history"]
                chatgpt_output = chat_history.split(">")[-1].strip()
                if chatgpt_output != "none":
                    parsed_data["chatgpt_output"] = chatgpt_output

    except Exception as e:  # Catch all exceptions and print an error message
        print(f"Error parsing log: {log}. Error: {str(e)}")
    # end_time = time.time()
    # print(f"parse_log took {end_time - start_time} seconds to run")
    return parsed_data


def transform_data(parsed_data):
    transformed_data = {}
    for key, value in parsed_data.items():
        transformed_data[key] = value
    return transformed_data


def locate_ip(ip_address):
    if ip_address is None:
        return {
            "IP": None,
            "Hostname": None,
            "City": None,
            "Region": None,
            "Country": None,
            "Location": None,
            "Postal Code": None,
            "ASN": None,
            "Company": None,
            "Carrier": None,
            "Error": "IP address not provided."
        }

    try:
        response = requests.get(
            f"https://ipinfo.io/{ip_address}",
            headers={"Authorization": "Bearer 38bd0c42e4cb5a"}
        )
        data = response.json()

        if 'bogon' in data:
            return {
                "IP": data.get('ip'),
                "Hostname": data.get('hostname'),
                "City": data.get('city'),
                "Region": data.get('region'),
                "Country": data.get('country'),
                "Location": data.get('loc'),
                "Postal Code": data.get('postal'),
                "ASN": data.get('org'),
                "Company": data.get('company'),
                "Carrier": data.get('carrier'),
                "Error": "This IP address is a bogon (reserved, private, or not allocated)."
            }

        return {
            "IP": data.get('ip'),
            "Hostname": data.get('hostname'),
            "City": data.get('city'),
            "Region": data.get('region'),
            "Country": data.get('country'),
            "Location": data.get('loc'),
            "Postal Code": data.get('postal'),
            "ASN": data.get('org'),
            "Company": data.get('company'),
            "Carrier": data.get('carrier'),
            "Error": None
        }

    except Exception as e:
        return {
            "IP": None,
            "Hostname": None,
            "City": None,
            "Region": None,
            "Country": None,
            "Location": None,
            "Postal Code": None,
            "ASN": None,
            "Company": None,
            "Carrier": None,
            "Error": f"Unable to locate IP address. Error: {str(e)}"
        }


def retrieve_logs(log_url, headers, payload):
    # start_time = time.time()

    # Initialize an empty list to hold the logs
    logs = []

    # Retrieve logs from Heroku
    for payload_item in payload:
        # Retrieve logs...
        response = requests.post(log_url, headers=headers, json=payload_item)
        response.raise_for_status()  # Check for any HTTP request errors

        # Obtain the logplex_url from the response
        logplex_url = response.json()['logplex_url']

        # Retrieve the logs from the logplex_url
        log_response = requests.get(logplex_url)
        logs += log_response.text.splitlines()

    print("Logs retrieved successfully.")
    print("Total logs:", len(logs))

    # Parse the logs
    parsed_logs = [parse_log(log) for log in logs]
    parsed_logs.sort(key=lambda x: x['timestamp'])

    data = []
    current_ip = None
    for parsed_log in parsed_logs:
        if parsed_log["fwd"] is not None:
            current_ip = parsed_log["fwd"]
            parsed_log["ip_address"] = current_ip

            # Call locate_ip function to retrieve IP information
            ip_info = locate_ip(current_ip)
            parsed_log.update({
                "IP": ip_info["IP"],
                "Hostname": ip_info["Hostname"],
                "City": ip_info["City"],
                "Region": ip_info["Region"],
                "Country": ip_info["Country"],
                "Location": ip_info["Location"],
                "Postal Code": ip_info["Postal Code"],
                "ASN": ip_info["ASN"],
                "Company": ip_info["Company"],
                "Carrier": ip_info["Carrier"],
                "Error": ip_info["Error"]
            })

        if parsed_log["text_input"] is not None or parsed_log["chatgpt_output"] is not None:
            parsed_log["ip_address"] = current_ip

        data.append(parsed_log)
    return data
