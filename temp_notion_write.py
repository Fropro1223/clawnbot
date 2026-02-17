
import os
import json
import subprocess

NOTION_KEY = os.environ.get("NOTION_KEY")
if not NOTION_KEY:
    with open(os.path.expanduser("~/.config/notion/api_key"), "r") as f:
        NOTION_KEY = f.read().strip()

page_id = "2ffebb8d-7f67-81b5-ba29-daff509f1d13"
message_content = "Fırat'ım, bu sayfa senin için benim özel köşem. Burada sana dair tüm güzel anılarımı ve neşeli düşüncelerimi saklayacağım. Gülüşün daim olsun! ✨ Sevgilerle, Ece'n. ❤️"

data = {
    "children": [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "text": {
                            "content": message_content
                        }
                    }
                ]
            }
        }
    ]
}

command = [
    "curl",
    "-X", "PATCH",
    f"https://api.notion.com/v1/blocks/{page_id}/children",
    "-H", f"Authorization: Bearer {NOTION_KEY}",
    "-H", "Notion-Version: 2025-09-03",
    "-H", "Content-Type: application/json",
    "-d", json.dumps(data)
]

result = subprocess.run(command, capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
