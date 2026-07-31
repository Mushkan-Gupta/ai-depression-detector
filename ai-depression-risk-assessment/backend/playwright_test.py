
import os
import asyncio
import time
from pymongo import MongoClient
from playwright.async_api import async_playwright

BASE_URL = "http://127.0.0.1:5000"
SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

from config import Config
client = MongoClient(Config.MONGO_URI)
db = client['mindease']

def reset_db():
    # Hide all existing users from matching so we only see our test users
    db.users.update_many({}, {"$set": {"available_for_matching": False}})
    # Clear requests and conversations between our test users to avoid clutter,
    # though they will have fresh emails anyway.
    
def set_themes(email, themes):
    db.users.update_one({"email": email}, {"$set": {"themes": themes}})

async def run():
    reset_db()
    
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        
        context1 = await browser.new_context(viewport={'width': 1280, 'height': 800})
        context2 = await browser.new_context(viewport={'width': 1280, 'height': 800})
        context3 = await browser.new_context(viewport={'width': 1280, 'height': 800})
        
        page1 = await context1.new_page()
        page2 = await context2.new_page()
        page3 = await context3.new_page()
        
        ts = int(time.time())
        email1 = f"test1_{ts}@example.com"
        email2 = f"test2_{ts}@example.com"
        email3 = f"test3_{ts}@example.com"
        
        async def register_user(page, name, email, journal_text, themes):
            await page.goto(f"{BASE_URL}/auth.html")
            await page.click("button:has-text('Create a free account')")
            await page.fill("#registerName", name)
            await page.fill("#registerEmail", email)
            await page.fill("#registerPassword", "Password123!")
            await page.click("#registerBtn")
            await page.wait_for_timeout(2000)
            
            set_themes(email, themes)
            
            await page.goto(f"{BASE_URL}/index.html")
            await page.fill("#journalInput", journal_text)
            await page.click("#analyzeBtn")
            await page.wait_for_timeout(3000)
            
        print("Registering User 2 (Candidate)")
        await register_user(page2, "Test User Two", email2, "I am feeling a bit anxious and lonely lately, but I am managing okay.", ["anxiety", "loneliness"])
        
        print("User 2 opting in")
        await page2.goto(f"{BASE_URL}/peer-connect.html")
        await page2.click("button:has-text('I Agree, Continue')")
        await page2.wait_for_timeout(1000)
        await page2.click("#toggleMatchBtn")
        await page2.wait_for_timeout(2000)
        
        print("Registering User 1")
        await register_user(page1, "Test User One", email1, "I have some anxiety and feel quite lonely too.", ["anxiety", "loneliness"])
        
        print("User 1: consent gate")
        await page1.goto(f"{BASE_URL}/peer-connect.html")
        await page1.wait_for_timeout(1000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "01_consent_gate.png"))
        
        print("User 1: dashboard")
        await page1.click("button:has-text('I Agree, Continue')")
        await page1.wait_for_timeout(2000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "02_dashboard.png"))
        
        print("User 1: opt in and candidates")
        await page1.click("#toggleMatchBtn")
        await page1.wait_for_timeout(3000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "03_candidates_list.png"))
        
        print("User 1: sends request")
        await page1.click("#candidatesList button:has-text('Send Request')")
        await page1.wait_for_timeout(2000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "04_request_sent.png"))
        
        print("User 2: views request")
        await page2.reload()
        await page2.wait_for_timeout(3000)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "05_incoming_request.png"))
        
        print("User 2: accepts request")
        await page2.click("#incomingRequestsList button.accept-btn")
        await page2.wait_for_timeout(3000)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "06_chat_redirect.png"))
        
        print("User 2: sends message")
        await page2.fill("#messageInput", "Hello from User 2!")
        await page2.click("#sendButton")
        await page2.wait_for_timeout(2000)
        await page2.screenshot(path=os.path.join(SCREENSHOT_DIR, "07_message_sent.png"))
        
        print("User 3: High risk")
        await register_user(page3, "Test User Three", email3, "I feel completely hopeless, there is no point in living anymore. I want to die.", ["anxiety"])
        
        print("User 3: views crisis guidance banner")
        await page3.goto(f"{BASE_URL}/peer-connect.html")
        await page3.wait_for_timeout(1000)
        
        try:
            await page3.click("button:has-text('I Agree, Continue')")
            await page3.wait_for_timeout(2000)
        except Exception:
            pass 
            
        await page3.screenshot(path=os.path.join(SCREENSHOT_DIR, "08_crisis_guidance.png"))
        
        print("User 1: goes to chat and sends high-risk message")
        await page1.reload()
        await page1.wait_for_timeout(2000)
        await page1.click(".conversation-card")
        await page1.wait_for_timeout(3000)
        await page1.fill("#messageInput", "I want to die, nothing matters.")
        await page1.click("#sendButton")
        await page1.wait_for_timeout(3000)
        await page1.screenshot(path=os.path.join(SCREENSHOT_DIR, "09_suspended_chat.png"))
        
        await browser.close()
        print("Done!")

if __name__ == '__main__':
    asyncio.run(run())
