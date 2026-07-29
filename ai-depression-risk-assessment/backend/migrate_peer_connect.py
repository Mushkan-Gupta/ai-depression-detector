import os
from pymongo import MongoClient
from pymongo.errors import CollectionInvalid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/mindease")

def migrate_peer_connect():
    print(f"Connecting to MongoDB at {MONGO_URI}...")
    client = MongoClient(MONGO_URI)
    db = client.get_default_database() if client.get_default_database().name else client['mindease']
    
    # 1. Update Users Collection Schema fields (No rigid schema enforcement needed in MongoDB, 
    # but we will ensure the index exists)
    print("Updating users collection indexes...")
    db.users.create_index(
        [
            ("available_for_matching", 1), 
            ("current_risk_level", 1), 
            ("matching_started_at", 1)
        ],
        name="idx_users_matching",
        partialFilterExpression={"available_for_matching": True}
    )
    print(" - Added idx_users_matching to users collection.")

    # 2. Create new collections with basic validation/indexes
    collections_to_create = [
        "connection_requests",
        "conversations",
        "messages",
        "reports"
    ]
    
    for coll_name in collections_to_create:
        try:
            db.create_collection(coll_name)
            print(f" - Created collection: {coll_name}")
        except CollectionInvalid:
            print(f" - Collection {coll_name} already exists. Skipping creation.")
            
    # Connection Requests Indexes
    db.connection_requests.create_index([("sender_id", 1), ("receiver_id", 1)])
    db.connection_requests.create_index([("status", 1)])
    
    # Conversations Indexes
    db.conversations.create_index([("participants", 1)])
    db.conversations.create_index([("status", 1)])
    
    # Messages Indexes
    db.messages.create_index([("conversation_id", 1), ("created_at", 1)])
    
    # Reports Indexes
    db.reports.create_index([("reported_by", 1)])
    db.reports.create_index([("reported_user", 1)])
    db.reports.create_index([("status", 1)])

    print("Migration completed successfully.")

if __name__ == "__main__":
    migrate_peer_connect()
