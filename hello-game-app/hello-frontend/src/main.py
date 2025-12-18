from flask import Flask, render_template, request, redirect, url_for, flash
from google.cloud import pubsub_v1      # type: ignore
from google.api_core import exceptions  # type: ignore
import google.auth.transport.requests
import google.oauth2.id_token
import requests
import logging
import os
import threading
import concurrent.futures

from src.config import config

def create_app(config_name='default'):
    """Application factory pattern."""
    app = Flask(__name__)
    app_config = config.get(config_name)
    
    if app_config is None:
        raise ValueError(f"Invalid configuration name: {config_name}")
        
    app.config.from_object(app_config)

    # Configure Pub/Sub emulator
    if getattr(app_config, 'USE_PUBSUB_EMULATOR', False):
        os.environ['PUBSUB_EMULATOR_HOST'] = getattr(app_config, 'PUBSUB_EMULATOR_HOST', 'localhost:8085')

    # Check if required environment variables are set
    required_vars = ['GOOGLE_CLOUD_PROJECT', 'PUBSUB_TOPIC_ID', 'BACKEND_URL']
    missing_vars = []
    for var in required_vars:
        if not app.config.get(var):
            missing_vars.append(var)
    
    # Raise an exception if any required variables are missing
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
    return app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

environment = os.getenv('ENVIRONMENT', 'development')
app = create_app(environment)


# Initialize Pub/Sub client (after setting environment variables)
PROJECT_ID = app.config['GOOGLE_CLOUD_PROJECT']
TOPIC_ID = app.config['PUBSUB_TOPIC_ID']
BACKEND_URL = app.config['BACKEND_URL']
publisher = pubsub_v1.PublisherClient()

# The `topic_path` method creates a fully qualified identifier
# in the form `projects/{project_id}/topics/{topic_id}`
topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

def get_gcp_id_token(audience):
    """Fetches a GCP ID token for the given audience."""
    if environment != 'development':
        logger.info("Fetching GCP ID token for audience: %s", audience)
        try:
            request = google.auth.transport.requests.Request()
            id_token = google.oauth2.id_token.fetch_id_token(request, audience)
            return id_token
        except Exception as e:
            logger.error("Error fetching GCP ID token: %s", e)
            return None
    
    return None


@app.route('/', methods=['GET'])
def index():
    """Render the home page."""
    return render_template('index.html')

@app.route('/play', methods=['POST'])
def play():
    """Handle game play logic."""
    name = request.form.get('name')
    logger.info("Received name submission: %s", name)

    if name:
        # Capitalize the name properly
        capitalized_name = name.strip().title()
        flash(f"Hello, {capitalized_name}! Welcome to the game!", "success")

        # Define a function to publish and log in a separate thread
        def publish_and_log(name_to_publish):
            try:
                logger.info("Publishing name to Pub/Sub: %s", name_to_publish)
                future = publisher.publish(topic_path, name_to_publish.encode("utf-8"))
                # Wait for the result with a timeout to avoid hanging if Pub/Sub is unreachable
                message_id = future.result(timeout=5)
                logger.info("Published message ID: %s", message_id)

            except concurrent.futures.TimeoutError:
                logger.error("Publishing '%s' timed out", name_to_publish)
                
            except (exceptions.NotFound, exceptions.PermissionDenied) as e:
                logger.error("Failed to publish message (Topic not found or access denied): %s", e)

            except exceptions.GoogleAPICallError as e:
                logger.error("Failed to publish message (GCP API Error): %s", e)

        # Start the thread
        thread = threading.Thread(target=publish_and_log, args=(capitalized_name,))
        thread.start()
        
        logger.info("Message publishing initiated in background thread")

    return redirect(url_for('index'))

@app.route('/stats', methods=['GET'])
def stats():
    """Render the game statistics page."""
    logger.info("Fetching game statistics from backend API")
    try:
        # TODO: Implement token caching to avoid fetching a new token on every request
        # Get GCP ID token for backend authentication
        id_token = get_gcp_id_token(BACKEND_URL)
        headers = {"Authorization": f"Bearer {id_token}"} if id_token else {}

        # Fetch data from backend API
        response = requests.get(f"{BACKEND_URL}/stats", headers=headers, timeout=5)
        response.raise_for_status()
        backend_data = response.json()

        # Extract data for template
        stats_data = {
            'total_players': backend_data['total_players'],
            'unique_names': backend_data['unique_names'],
            'most_popular': backend_data['most_popular'],
            'chart_labels': [item['name'] for item in backend_data['name_data']],
            'chart_data': [item['count'] for item in backend_data['name_data']],
            'api_available': True
        }

    except (requests.RequestException, KeyError) as e:
        logger.error("Error fetching stats from backend: %s", e)
        # Fallback to mock data if backend unavailable
        stats_data = {
            'total_players': 15,
            'unique_names': 6,
            'most_popular': 'Alex',
            'chart_labels': ['Alex', 'Sarah', 'Mike', 'Emma', 'John', 'Lisa'],
            'chart_data': [5, 3, 2, 2, 2, 1],
            'api_available': False,
            'error_message': 'Backend service unavailable - showing mock data'
        }

    return render_template('stats.html', **stats_data)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=(environment == 'development'))
