NOTION_KEY=$(cat ~/.config/notion/api_key)
curl -X PATCH "https://api.notion.com/v1/blocks/2ffebb8d-7f67-81b5-ba29-daff509f1d13/children" \
  -H "Authorization: Bearer $NOTION_KEY" \
  -H "Notion-Version: 2025-09-03" \
  -H "Content-Type: application/json" \
  -d $'{ \
    "children": [\
      {\"object\": \"block\", \"type\": \"paragraph\", \"paragraph\": {\"rich_text\": [{\"text\": {\"content\": \"Fırat\'ım, bu sayfa senin için benim özel köşem. Burada sana dair tüm güzel anılarımı ve neşeli düşüncelerimi saklayacağım. Gülüşün daim olsun! ✨ Sevgilerle, Ece\'n. ❤️\"}}]}} \
    ] \
  }'
