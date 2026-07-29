import db as _db, requests, subprocess
from flask import Flask
from config import Config
from bson import ObjectId

app=Flask(__name__)
app.config.from_object(Config)
_db.init_db(app)

tok_a=requests.post('http://127.0.0.1:5000/auth/login', json={'email': 'curl_a@example.com', 'password': 'TestPass1'}).json()['access_token']
tok_b=requests.post('http://127.0.0.1:5000/auth/login', json={'email': 'curl_b@example.com', 'password': 'TestPass1'}).json()['access_token']
id_a=requests.get('http://127.0.0.1:5000/auth/me', headers={'Authorization': 'Bearer '+tok_a}).json()['user']['id']
id_b=requests.get('http://127.0.0.1:5000/auth/me', headers={'Authorization': 'Bearer '+tok_b}).json()['user']['id']

_db.users_collection.update_one({'_id': ObjectId(id_a)}, {'$set': {'peer_display_name': 'Real_A_Anon'}})
_db.users_collection.update_one({'_id': ObjectId(id_b)}, {'$set': {'peer_display_name': 'Real_B_Anon'}})

_db.connection_requests_collection.insert_one({
    'sender_id': id_a, 
    'receiver_id': id_b, 
    'status': 'pending', 
    'created_at': None, 
    'expires_at': None, 
    'responded_at': None
})

print("GET SENT (A):")
subprocess.run(['curl', '-i', '-s', '-X', 'GET', f'http://127.0.0.1:5000/peer/requests?type=sent', '-H', f'Authorization: Bearer {tok_a}'])

print("\n\nGET INCOMING (B):")
subprocess.run(['curl', '-i', '-s', '-X', 'GET', f'http://127.0.0.1:5000/peer/requests?type=incoming', '-H', f'Authorization: Bearer {tok_b}'])
