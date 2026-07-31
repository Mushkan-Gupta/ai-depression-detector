import os
import asyncio
import time
from pymongo import MongoClient
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = "screenshots_visual"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

from config import Config
client = MongoClient(Config.MONGO_URI)
db = client['mindease']

def reset_db():
    db.users.update_many({}, {"$set": {"available_for_matching": False}})

async def run():
    reset_db()
    
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        
        context1 = await browser.new_context(viewport={'width': 1280, 'height': 800})
        context2 = await browser.new_context(viewport={'width': 1280, 'height': 800})
        
        page1 = await context1.new_page()
        page2 = await context2.new_page()
        
        ts = int(time.time())
        email1 = f"alice_{ts}@example.com"
        email2 = f"bob_{ts}@example.com"
        
        journal_text = "I am feeling a bit anxious and lonely lately, but I am managing okay."
        
        async def register_user(page, name, email, journal_text):
            await page.goto(f"{BASE_URL}/auth.html")
            await page.click("button:has-text('Create a free account')")
            await page.fill("#registerName", name)
            await page.fill("#registerEmail", email)
            await page.fill("#registerPassword", "Password123!")
            await page.click("#registerBtn")
            await page.wait_for_timeout(2000)
            
            # NO MANUAL THEME INJECTION HERE
            
            await page.goto(f"{BASE_URL}/index.html")
            await page.fill("#journalInput", journal_text)
            await page.click("#analyzeBtn")
            await page.wait_for_timeout(3000)
            
        print("Registering Alice (User 1)")
        await register_user(page1, "Alice User", email1, journal_text)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_alice_journal.png"))
        
        print("Alice opting in to Peer Connect")
        await page1.goto(f"{BASE_URL}/peer-connect.html")
        await page1.wait_for_timeout(1000)
        await page1.click("button:has-text('I Agree, Continue')")
        await page1.wait_for_timeout(1000)
        await page1.click("#toggleMatchBtn")
        await page1.wait_for_timeout(2000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_alice_opted_in.png"))
        
        print("Registering Bob (User 2) with EXACT SAME journal")
        await register_user(page2, "Bob User", email2, journal_text)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_bob_journal.png"))
        
        print("Bob opting in to Peer Connect")
        await page2.goto(f"{BASE_URL}/peer-connect.html")
        await page2.wait_for_timeout(1000)
        await page2.click("button:has-text('I Agree, Continue')")
        await page2.wait_for_timeout(1000)
        await page2.click("#toggleMatchBtn")
        await page2.wait_for_timeout(2000)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_bob_candidates.png"))
        
        print("Checking if Alice appears in Bob's candidates list...")
        send_req_btn = page2.locator("#candidatesList button:has-text('Send Request')")
        count = await send_req_btn.count()
        
        if count == 0:
            print("PROBLEM DETECTED: No candidates found!")
            print("Report: Bob and Alice have the exact same journal, but Bob's candidate list is empty.")
            print("Root Cause: The /predict endpoint calculates themes on the frontend (analyze.js) but never saves them to the MongoDB users_collection. The backend peer matcher requires overlapping_themes, which evaluates to 0 because both users have an empty themes array in the DB.")
            
            print("WORKAROUND: Injecting themes manually to continue the flow...")
            db.users.update_one({"email": email1}, {"$set": {"themes": ["anxiety", "loneliness"]}})
            db.users.update_one({"email": email2}, {"$set": {"themes": ["anxiety", "loneliness"]}})
            
            await page2.reload()
            await page2.wait_for_timeout(3000)
            await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "04b_bob_candidates_fixed.png"))
        
        print("Bob: sends request to Alice")
        await page2.click("#candidatesList button:has-text('Send Request')")
        await page2.wait_for_timeout(2000)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_bob_request_sent.png"))
        
        print("Alice: views incoming request")
        await page1.reload()
        await page1.wait_for_timeout(3000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_alice_incoming_request.png"))
        
        print("Alice: accepts request")
        await page1.click("#incomingRequestsList button.accept-btn")
        await page1.wait_for_timeout(3000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_alice_chat_redirect.png"))
        
        print("Alice: sends message to Bob")
        await page1.fill("#messageInput", "Hi Bob, I see we matched!")
        await page1.click("#sendButton")
        await page1.wait_for_timeout(2000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_alice_message_sent.png"))
        
        print("Bob: goes to chat and views message")
        await page2.reload()
        await page2.wait_for_timeout(2000)
        await page2.click(".conversation-card")
        await page2.wait_for_timeout(3000)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_bob_chat_received.png"))
        
        print("Bob: replies to Alice")
        await page2.fill("#messageInput", "Hello Alice! Yes, we have similar feelings.")
        await page2.click("#sendButton")
        await page2.wait_for_timeout(2000)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "10_bob_message_sent.png"))
        
        await browser.close()
        print("Done!")

if __name__ == '__main__':
    asyncio.run(run())
