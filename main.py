from flask import Flask, request, jsonify
import requests
import re
import os
from xml.etree import ElementTree as ET

app = Flask(__name__)

BOT_TOKEN = os.environ['BOT_TOKEN']
YOUR_CHAT_ID = os.environ['YOUR_CHAT_ID']
CHANNEL_USERNAME = os.environ.get('CHANNEL_USERNAME', '@shock_news_com')

def send_photo(chat_id, photo_url, caption="", buttons=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {'chat_id': chat_id, 'photo': photo_url, 'caption': caption[:200]}
    if buttons:
        data['reply_markup'] = buttons
    requests.post(url, data=data)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.json
    if 'callback_query' in update:
        query = update['callback_query']
        chat_id = query['message']['chat']['id']
        msg_id = query['message']['message_id']
        data = query['data']
        
        if data == 'reject':
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText", 
                         data={'chat_id': chat_id, 'message_id': msg_id, 'text': '❌ Отклонено'})
        elif data.startswith('approve_'):
            _, image_url, text = data.split('|', 2)
            send_photo(CHANNEL_USERNAME, image_url, text)
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText",
                         data={'chat_id': chat_id, 'message_id': msg_id, 'text': f'✅ Опубликовано:\n{text}'})
    return jsonify(ok=True)

@app.route('/fetch', methods=['GET'])
def fetch_posts():
    feeds = ['https://meduza.io/rss/all', 'https://9gag.com/rss']
    for feed in feeds:
        try:
            resp = requests.get(feed, timeout=10)
            root = ET.fromstring(resp.content)
            for item in root.findall('.//item')[:2]:
                title = item.findtext('title', '')
                desc = item.findtext('description', '')
                text = re.sub(r'<[^>]+>', '', title + ' ' + desc).strip()
                text = re.sub(r'https?://[^\s]+', '', text)[:120].rstrip('.!? ')
                
                image_url = ''
                enclosure = item.find('enclosure')
                if enclosure is not None:
                    image_url = enclosure.get('url', '')
                if not image_url:
                    media = item.find('{http://search.yahoo.com/mrss/}content')
                    if media is not None:
                        image_url = media.get('url', '')
                
                if text and image_url:
                    buttons = '{"inline_keyboard":[[{"text":"✅ Одобрить","callback_data":"approve_|' + image_url + '|' + text + '"},{"text":"❌ Отклонить","callback_data":"reject"}]]}'
                    send_photo(YOUR_CHAT_ID, image_url, text, buttons)
        except Exception as e:
            print("Ошибка:", e)
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8000)))
