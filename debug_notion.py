import os
import requests
import json
from dotenv import load_dotenv

# Load env
load_dotenv()

def verify_notion():
    print("📘 Checking Notion Access...")
    
    token = os.getenv("NOTION_API_KEY")
    if not token:
        print("❌ Error: NOTION_API_KEY not found in .env")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    
    try:
        # Search endpoint matches all pages bot has access to
        url = "https://api.notion.com/v1/search"
        payload = {"page_size": 5}
        
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("results", [])
            print(f"✅ Connection Successful!")
            print(f"📄 Accessible Objects: {len(results)}")
            
            if not results:
                print("\n⚠️  No pages found! (You need to 'Add Connection' > 'Ece' in Notion pages)")
            else:
                for item in results:
                    obj_type = item.get("object")
                    title = "Untitled"
                    if obj_type == "page":
                        props = item.get("properties", {})
                        # Try to find title in various property types
                        for key, val in props.items():
                            if val.get("id") == "title":
                                title_list = val.get("title", [])
                                if title_list:
                                    title = title_list[0].get("plain_text", "Untitled")
                                break
                    elif obj_type == "database":
                         title_list = item.get("title", [])
                         if title_list:
                             title = title_list[0].get("plain_text", "Untitled")
                    
                    print(f"   - [{obj_type.upper()}] {title}")
                    
        else:
            print(f"❌ Connection Failed: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    verify_notion()
