# -*- coding: utf-8 -*-
"""
diagnose_predict.py
===================
Imports the app directly (no HTTP) and calls predict logic inline
to see exactly what JWT returns and whether MongoDB saves work.
"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Simulate Flask context
from app import app
from db import journal_entries_collection
from flask_jwt_extended import create_access_token, decode_token
from bson import ObjectId
from datetime import datetime, timezone
import json

print("\n" + "="*60)
print("  DIAGNOSE: JWT + MongoDB Save")
print("="*60)

with app.app_context():
    # Create a token the same way auth_routes now does
    user_id = str(ObjectId())
    print(f"\n[1] Creating token with identity (string): {user_id!r}")
    
    token = create_access_token(
        identity=user_id,
        additional_claims={"email": "test@test.com", "name": "Test"}
    )
    print(f"    Token created: {token[:60]}...")
    
    # Decode it back
    decoded = decode_token(token)
    sub = decoded.get("sub")
    print(f"\n[2] Decoded 'sub': {sub!r}  (type={type(sub).__name__})")
    print(f"    Full decoded payload: {json.dumps({k:v for k,v in decoded.items() if k != 'jti'}, indent=4)}")
    
    # Test direct MongoDB insert
    print(f"\n[3] Attempting direct MongoDB insert...")
    try:
        result = journal_entries_collection.insert_one({
            "user_id":    user_id,
            "journal":    "Test journal entry from diagnostic script.",
            "risk":       "Low",
            "confidence": 0.75,
            "created_at": datetime.now(timezone.utc),
        })
        print(f"    Insert OK! inserted_id={result.inserted_id}")
        
        # Verify it's there
        found = journal_entries_collection.find_one({"_id": result.inserted_id})
        if found:
            print(f"    Verified in DB: risk={found['risk']}  user_id={found['user_id']}")
        else:
            print("    ERROR: Could not retrieve inserted document!")
            
        # Clean up
        journal_entries_collection.delete_one({"_id": result.inserted_id})
        print(f"    Cleaned up test entry.")
    except Exception as e:
        print(f"    FAILED: {e}")

    # Now simulate what verify_jwt_in_request does with the new token
    print(f"\n[4] Simulating verify_jwt_in_request with new token...")
    from flask import request as flask_request
    from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
    
    # Build a fake request context
    with app.test_request_context(
        '/predict',
        method='POST',
        headers={'Authorization': f'Bearer {token}'},
        json={'journal': 'test text'}
    ):
        try:
            verify_jwt_in_request(optional=True)
            identity = get_jwt_identity()
            print(f"    verify_jwt_in_request OK!")
            print(f"    identity = {identity!r}  (type={type(identity).__name__})")
        except Exception as e:
            print(f"    FAILED: {type(e).__name__}: {e}")

print("\n" + "="*60 + "\n")
