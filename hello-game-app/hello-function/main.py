import base64
import logging
import os
from google.cloud.sql.connector import Connector, IPTypes
import pg8000

# Database configuration
INSTANCE_CONNECTION_NAME = os.getenv('INSTANCE_CONNECTION_NAME', '')
DB_NAME = os.getenv('DB_NAME', 'hello_game_submissions')
DB_USER = os.getenv('DB_USER', 'hello_user')

INSERT_QUERY = """
    INSERT INTO game_submissions (name, submitted_at)
    VALUES (%s, NOW());
"""

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def process_pubsub_message(event, context):
    """
    Background Cloud Function to be triggered by Pub/Sub.
    Args:
         event: Contains the Pub/Sub message data
        context: Contains metadata (timestamp, event_id, etc.)
    """
    logger.info(f"Received event ID: {context.event_id} at {context.timestamp}")

    if 'data' in event:
        pubsub_message = base64.b64decode(event['data']).decode('utf-8')
        logger.info(f"Decoded Pub/Sub message: {pubsub_message}")
        
        # Save the name to the database
        connector = Connector()
        db = connector.connect(
            instance_connection_string=INSTANCE_CONNECTION_NAME,
            driver="pg8000",
            user=DB_USER,
            db=DB_NAME,
            enable_iam_auth=True,     # IAM-based passwordless auth
            ip_type=IPTypes.PRIVATE,  # PRIVATE or PUBLIC
        )

        # Insert the name into the database in try block to close connection properly on error
        try:
            cursor = db.cursor()
            insert_query = INSERT_QUERY
            cursor.execute(insert_query, (pubsub_message.strip().title(),))
            cursor.close()
            db.commit()
            logger.info(f"Inserted name '{pubsub_message}' into database.")
        
        except Exception as e:
            logger.error(f"Error inserting name into database: {e}")
            raise # Reraise exception to signal failure to Pub/Sub

        finally:
            db.close()
            connector.close()
            logger.info("Database connection closed.")
        
    else:
        logger.warning("No data found in Pub/Sub message.")


if __name__ == "__main__":
    """Test the function locally with mock data."""
    from datetime import datetime
    
    # Mock Pub/Sub event data
    mock_event = {
        'data': base64.b64encode("TestUser".encode('utf-8')).decode('utf-8')
    }
    
    # Mock context object
    class MockContext:
        def __init__(self):
            self.event_id = 'test-event-123'
            self.timestamp = datetime.now().isoformat()
    
    mock_context = MockContext()
    
    print("Testing Cloud Function with mock data...")
    print(f"Mock message: TestUser")
    
    try:
        process_pubsub_message(mock_event, mock_context)
        print("✅ Function executed successfully!")
    except Exception as e:
        print(f"❌ Function failed: {e}")
