import os
from dotenv import load_dotenv
from flask import Flask, request, render_template, redirect, send_file, flash
import requests
import unittest
from googletrans import Translator
import datetime
import boto3
from botocore.exceptions import ClientError
import logging
from decimal import Decimal

app = Flask(__name__)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_weather_results(location, key, unit):
    try:
        api_url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/next6days?unitGroup={unit}&key={key}&contentType=json"
        with requests.get(api_url) as r:
            data = r.json()
        next_week_weather = []
        translator = Translator()

        country = data.get('resolvedAddress', '')
        translated_country = translator.translate(country, dest='en').text
        for day in data['days']:
            next_week_weather.append({
                "date": day["datetime"],
                "day_temperature": Decimal(str(day.get("tempmax"))),
                "night_temperature": Decimal(str(day.get("tempmin"))),
                "humidity": Decimal(str(day.get("humidity")))
            })

        return {
            "location": translated_country,
            "weather": next_week_weather,
            "origin_language": country,
            "unit": unit
        }
    except Exception as e:
        print(f"Error occurred: {e}")
        return None


def save_to_dynamodb(location, weather_info):
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('Weather')

    try:
        response = table.put_item(
            Item={
                'location': location,
                'timestamp': str(datetime.datetime.utcnow()), 
                'weather_info': weather_info
            }
        )
        logger.info(f"Successfully saved data to DynamoDB: {response}")
        return True
    except ClientError as e:
        logger.error(f"Failed to save data to DynamoDB: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return False


@app.route("/", methods=["GET", "POST"])
def home_page():
    weather_info = None
    if request.method == "POST":
        location = request.form.get("location")
        unit = request.form.get("unit", "metric")
        action = request.form.get("action")

        if action == "download":
            return redirect("/download-image")

        if location:
            key = os.getenv('API_KEY')
            weather_info = get_weather_results(location, key, unit)
            if weather_info is None:
                weather_info = {"location": location, "error": "Could not retrieve weather information."}
            else:
                if action == "origin_language":
                    weather_info["display_location"] = weather_info["origin_language"]
                else:
                    weather_info["display_location"] = weather_info["location"]

                if action == "save":
                    if save_to_dynamodb(location, weather_info):
                        flash("Weather information saved to DynamoDB successfully!")
                    else:
                        flash("Failed to save weather information to DynamoDB.")

    return render_template("index.html", weather_info=weather_info)


@app.route("/download-image", methods=["GET"])
def download_image():
    s3_url = 'https://hadar-static-bucket.s3.amazonaws.com/hapoel.jpeg'
    local_filename = 'hapoel.jpeg'

    # Download the file from S3 to the local filesystem
    with requests.get(s3_url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

    # Send the file to the user for download
    return send_file(local_filename, as_attachment=True)


class Testing(unittest.TestCase):
    def test_connectivity(self):
        with app.test_client() as client:
            response = client.options('/')
            self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(Testing)
    test_result = unittest.TextTestRunner().run(test_suite)

    if test_result.wasSuccessful():
        app.run()
    else:
        print("Unittests failed")
        exit(1)
