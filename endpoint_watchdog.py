import os
import argparse
current_pid = os.getpid()
import requests
import subprocess

import datetime
import time
subprocess.run(["python3", "-m", "pip", "install", "pytz"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
import pytz
subprocess.run(["python3", "-m", "pip", "install", "tzlocal"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
from tzlocal import get_localzone

import re
import sys

# for discord bot
subprocess.run(["python3", "-m", "pip", "install", "python-dotenv"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
from dotenv import load_dotenv
import socket
import hashlib
import json
import difflib
import canonicaljson


# Constants
DPASTE_MAX_LENGTH = 1000000
DISCORD_MAX_LENGTH = 2000
CACHE_FILE = "endpoint_cache.json"

# Updates
auto_update_enabled = True
UPDATE_INTERVAL_MULTIPLIER = 5  # number of iterations before checking for updates

# Timestamp pattern
timestamp_pattern = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d{3}Z')

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define the path to the .env file
env_file = os.path.join(script_dir, '.env')


def initialize_env_file(env_file_path):
    # Load existing environment variables from the .env file if it exists
    if os.path.exists(env_file_path):
        load_dotenv(env_file_path)

    # Check for ENDPOINT_URL
    endpoint_url = os.getenv('ENDPOINT_URL')
    if not endpoint_url:
        print("Endpoint URL is required to run this script.")
        endpoint_url = input("Please enter the endpoint URL: ").strip()
    validate_endpoint(endpoint_url)

    # Check for ENDPOINT_URL
    watch_interval = os.getenv('WATCH_INTERVAL')
    if not watch_interval:
        print("Watch Interval is required to run this script.")
        watch_interval = input("Please enter the watch interval in minutes: ").strip()
    if not int(watch_interval):
        print("Watch Interval invalid! Setting to 1 minute.")
        watch_interval = 1

    # Check for DISCORD_WEBHOOK_URL
    notify_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
    if not notify_webhook_url:
        print("Discord notify_webhook URL is required to run this script.")
        notify_webhook_url = input("Please enter your Discord notify_webhook URL: ").strip()
        while not notify_webhook_url.startswith("https://discord.com/api/webhooks/"):
            print("Invalid notify_webhook URL. It should start with 'https://discord.com/api/webhooks/'")
            notify_webhook_url = input("Please enter a valid Discord notify_webhook URL: ").strip()
    #validate_notify_webhook(endpoint_url, notify_webhook_url)
    
    # Check for DISCORD_MENTION_CODE
    notify_mention_code = os.getenv('DISCORD_MENTION_CODE')
    if not notify_mention_code:
        print("Discord mention code is required to run this script.")
        notify_mention_code = input("Please enter your Discord mention code: ").strip()
        while not re.match(r'<@&\d+>', notify_mention_code):
            print("Invalid mention code. It should be in the format '<@&1234567890>'")
            notify_mention_code = input("Please enter a valid Discord mention code: ").strip()
    
    # Check for FIELDS_TO_IGNORE (a CSV of JSON fields to ignore in the diff)
    fields_to_ignore = os.getenv('FIELDS_TO_IGNORE')
    if not fields_to_ignore:
        print("Fields to ignore (CSV) are required to run this script.")
        fields_to_ignore = input("Please enter the fields to ignore as a comma-separated list: ").strip()
    fields_to_ignore = [field.strip() for field in fields_to_ignore.split(',') if field.strip()]


    # Save both URLs to the .env file
    with open(env_file_path, 'w') as f:
        f.write(f'ENDPOINT_URL={endpoint_url}\n')
        f.write(f'WATCH_INTERVAL={int(watch_interval)}\n')
        f.write(f'FIELDS_TO_IGNORE={",".join(fields_to_ignore)}\n')
        f.write(f'DISCORD_WEBHOOK_URL={notify_webhook_url}\n')
        f.write(f'DISCORD_MENTION_CODE={notify_mention_code}\n')

    print(f"Endpoint URL, Watch Interval, and Webhook URL have been saved to {env_file_path}")
    return endpoint_url, watch_interval, fields_to_ignore, notify_webhook_url, notify_mention_code


def validate_endpoint(endpoint_url):
    try:
        response = requests.get(endpoint_url)
        if response.status_code == 200:
            print("Endpoint validation successful!")
            return True
        else:
            print(f"Endpoint validation failed. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error validating endpoint: {str(e)}")
        return False


def validate_notify_webhook(endpoint_url, notify_webhook_url):
    try:
        response = requests.post(notify_webhook_url, json={"content": f"Endpoint Monitor:\n\nWebhook test for monitoring {endpoint_url}"})
        if response.status_code == 204:
            print("Webhook test successful!")
            return True
        else:
            print(f"Webhook test failed. Status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"Error testing notify_webhook: {str(e)}")
        return False


def get_host_ip(api_token=None):
    headers = {'Authorization': f'Bearer {api_token}'} if api_token else {}
    try:
        response = requests.get('https://ipinfo.io', headers=headers)
        ip_info = response.json()
        IP = ip_info['ip']
    except Exception as e:
        print(f"Error getting IP information: {e}")
        IP = '127.0.0.1'
    return IP


def get_system_uptime():
    try:
        result = subprocess.run(["uptime", "-p"], capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error getting system uptime: {e}"


def report_for_duty(endpoint_url, message_topic, message_contents, notify_webhook_url, is_initial_check=False, diff_content=None):
    # Message content
    host_ip = get_host_ip()
    host_name = socket.gethostname() 
    os.chdir(os.path.dirname(__file__))
    commit_before_pull = get_latest_commit_hash()
    system_uptime = get_system_uptime()

    # if initialized, if diff, else if error
    initial_greeting = "Initialized" if is_initial_check else "Changes Detected" if diff_content else "Error"
    
    greeting = f"# :eyes: _Endpoint Watchdog {initial_greeting}!_\n" + \
              f"**Endpoint URL:** {endpoint_url}\n\n" + \
              f"**Host Name:** {host_name}\n" + \
              f"**Host IP:** {host_ip}\n" + \
              f"**Commit Hash:** {commit_before_pull}\n" + \
              f"**System Uptime:** {system_uptime}\n"
              
    message = greeting + \
              f"**{message_topic} Details:**\n\n{message_contents}\n\n"
                      
    if diff_content or len(message) > DISCORD_MAX_LENGTH:
        # Post lengthy message to dpaste and get the link
        dpaste_link = post_to_dpaste(diff_content or message)
        short_message = (message if diff_content else greeting) + \
                        f"[View full report]({dpaste_link})"
        data = {
            "content": short_message,
            "username": host_ip
        }
    else:
        data = {
            "content": message,
            "username": host_ip
        }

    response = requests.post(notify_webhook_url, json=data)
    if response.status_code == 204:
        print(f"[{datetime.datetime.now()}] Message sent successfully")
    else:
        print(f"[{datetime.datetime.now()}] Failed to send message, status code: {response.status_code}")


def post_to_dpaste(content, syntax="diff", expires=30):

    # dpaste API endpoint
    api_url = 'https://dpaste.com/api/v2/'

    # Data to be sent to dpaste
    headers = {"User-Agent": "Mozilla/5.0"}
    data = {
        "syntax": syntax,
        "expiry_days": expires,
        "content": content,
    }

    # Make the POST request
    response = requests.post(api_url, data=data, headers=headers)

    if response.status_code == 201:
        # Return the URL of the snippet
        return response.text.strip()
    
    # Return an error message or raise an exception
    print(response.text)
    return f"Failed to create dpaste snippet. Status code: {response.status_code}"


def get_latest_commit_hash():
    """Function to get the latest commit hash."""
    result = subprocess.run(["git", "log", "-1", "--format=%H"], capture_output=True, text=True)
    return result.stdout.strip()


def check_for_updates():
    os.chdir(os.path.dirname(__file__))
    commit_before_pull = get_latest_commit_hash()
    subprocess.run(["git", "pull"], check=True)
    commit_after_pull = get_latest_commit_hash()

    if commit_before_pull != commit_after_pull:
        print("Updates pulled, exiting...")
        exit(0)
    else:
        print("No updates found, continuing...")
        return time.time()


def remove_fields(data, fields):
    if isinstance(data, dict):
        return {
            key: remove_fields(value, fields)
            for key, value in data.items()
            if key not in fields
        }
    elif isinstance(data, list):
        return [remove_fields(item, fields) for item in data]
    return data


def fetch_and_format_response(url, fields_to_ignore=None):
    """
    Fetch and format the JSON response from the given URL.
    """
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch response from {url}. Status code: {response.status_code}")
    try:
        json_data = response.json()  # Parse JSON

        # Remove fields to ignore and canonicalize the JSON
        json_data = remove_fields(json_data, fields_to_ignore or [])
        json_data = canonicaljson.encode_canonical_json(json_data).decode('utf-8')
                
        #json_data = json.dumps(json_data, indent=4)  # Pretty format
        return json_data.splitlines()  # Split into lines for processing
    except ValueError as e:
        raise Exception("Failed to parse response as JSON") from e


def generate_diff(old_data, new_data):
    
    # Split the data into lines
    old_data = old_data.splitlines()
    new_data = new_data.splitlines()
    
    diff = difflib.unified_diff(
        old_data,
        new_data,
        lineterm='',
        fromfile='Cached Response',
        tofile='New Response'
    )
    return "\n".join(diff)


def calculate_hash(data):
    """
    Calculate a hash for the formatted JSON data.
    """
    return hashlib.md5("\n".join(data).encode()).hexdigest()


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)


def process_endpoint_response(endpoint_url, notify_webhook_url, notify_mention_code, fields_to_ignore=None, is_initial_check=False):
    print(f"[{datetime.datetime.now()}] Processing Endpoint Response...")

    # Load or initialize cache
    cache = load_cache()
    cached_response = cache.get('response', [])
    endpoint_response = fetch_and_format_response(endpoint_url, fields_to_ignore)
    response_hash = calculate_hash(endpoint_response)
    response_length = len("\n".join(endpoint_response))

    # Create the message
    if is_initial_check:
        message = (
            f":white_check_mark: Endpoint Watchdog Initialized!\n\n"
            f"**Initial Response Length:** {response_length}\n"
            f"**Initial Response Hash:** {response_hash}\n"
        )
        
        save_cache({'response': endpoint_response, 'hash': response_hash})
        report_for_duty(endpoint_url, "Script Started", message, notify_webhook_url, is_initial_check)
        print(f"[{datetime.datetime.now()}] Initial check completed.")
        
    elif response_hash == cache.get('hash'):
        print(f"[{datetime.datetime.now()}] No changes detected in the endpoint response.")

    else:
        # Generate a diff
        diff = generate_diff(cached_response, endpoint_response)
        diff_snippet = diff if len(diff) <= DPASTE_MAX_LENGTH else f"{diff[:DPASTE_MAX_LENGTH]}...\n[Diff truncated]"

        # Save updated cache
        message = (
            f":warning: {notify_mention_code} Endpoint changes detected!\n\n"
            f"**New Response Length:** {response_length}\n"
            f"**New Response Hash:** {response_hash}\n\n"
        )
        report_for_duty(endpoint_url, "Endpoint Changes", message, notify_webhook_url, is_initial_check=False, diff_content=diff_snippet)
        print(f"[{datetime.datetime.now()}] Changes detected and reported.")

        save_cache({'response': endpoint_response, 'hash': response_hash})



def main():

    # Load .env file, or initialize it if it doesn't exist
    endpoint_url, watch_interval, fields_to_ignore, notify_webhook_url, notify_mention_code = initialize_env_file(env_file)

    # Check Updates
    if auto_update_enabled:
        update_start_time = check_for_updates()
        
    # Perform the initial check and report
    process_endpoint_response(endpoint_url, notify_webhook_url, notify_mention_code, fields_to_ignore, is_initial_check=True)

    # Initialize the watchdog liveness timer
    watchdog_liveness = time.time()

    # Commands for system setup commented out for brevity
    while True:
        try:
            if int(time.time() - watchdog_liveness) >= int(watch_interval) * 60:

                # Uptime liveness check
                process_endpoint_response(endpoint_url, notify_webhook_url, notify_mention_code, fields_to_ignore)

                watchdog_liveness = time.time()

            # Updates
            if auto_update_enabled and time.time() - update_start_time >= int(watch_interval) * 60 * UPDATE_INTERVAL_MULTIPLIER:
                update_start_time = check_for_updates()

            time.sleep(1) # 1 second minimum
        except Exception as e:
            report_for_duty(endpoint_url, "Error", f"An error occurred in the Endpoint monitor script: {str(e)}", notify_webhook_url)
            break


if __name__ == "__main__":
    main()
