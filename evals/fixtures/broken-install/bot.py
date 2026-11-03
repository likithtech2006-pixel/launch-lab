import os
import slack_sdk  # not in requirements.txt
import requests

API_KEY = os.environ["WEATHER_API_KEY"]
SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN")
