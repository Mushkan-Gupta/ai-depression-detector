import json
from app import app
import db as _db
from constants.keywords import THEME_MAP
from flask_jwt_extended import create_access_token

emails_to_check = ['mushkanguptahere@gmail.com', 'gmushkan49@gmail.com']

with app.app_context():
    users = list(_db.users_collection.find({}))
    total_users = len(users)
    updated_users = 0
    
    for u in users:
        user_id = str(u['_id'])
        
        # fetch all journal entries for this user
        entries = list(_db.journal_entries_collection.find({"user_id": user_id}))
        
        detected_themes_set = set()
        for entry in entries:
            journal_text = entry.get("journal", "")
            lower_journal = journal_text.lower()
            
            for t_obj in THEME_MAP:
                if any(kw in lower_journal for kw in t_obj["keywords"]):
                    detected_themes_set.add(t_obj["theme"])
                    
        detected_themes = list(detected_themes_set)
        
        if detected_themes:
            # Update user doc
            res = _db.users_collection.update_one(
                {"_id": u['_id']},
                {"$addToSet": {"themes": {"$each": detected_themes}}}
            )
            if res.modified_count > 0:
                updated_users += 1

    print(f"Total users processed: {total_users}")
    print(f"Users with themes added/updated: {updated_users}")
    
    print("\n--- UPDATED THEMES FOR REAL ACCOUNTS ---")
    real_users = list(_db.users_collection.find({"email": {"$in": emails_to_check}}))
    user_ids = {}
    for ru in real_users:
        print(f"Email: {ru['email']}")
        print(f"Themes: {ru.get('themes', [])}")
        user_ids[ru['email']] = str(ru['_id'])
        
    print("\n--- API RESPONSES AFTER BACKFILL ---")
    with app.test_client() as client:
        for email, uid in user_ids.items():
            access_token = create_access_token(identity=uid)
            headers = {"Authorization": f"Bearer {access_token}"}
            res = client.get("/peer/candidates", headers=headers)
            print(f"Response for {email}:")
            print(res.status_code)
            print(res.get_data(as_text=True))
