import os
import requests
from flask import Flask, render_template, send_from_directory
from bs4 import BeautifulSoup

app = Flask(__name__)

BING_URL = "https://www.bing.com"
IMAGE_DIR = os.path.join(app.static_folder, "images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def get_bing_wallpaper():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0 Safari/537.36'
        }
        r = requests.get(f"{BING_URL}/", headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        bg_image = None
        body = soup.find('body', style=True)
        if body:
            style = body['style']
            start = style.find('url(') + 4
            end = style.find(')', start)
            if start != -1 and end != -1:
                bg_image = BING_URL + style[start:end].strip("'\"")

        if not bg_image:
            meta = soup.find('meta', {'property': 'og:image'})
            if meta and meta.get('content'):
                img_url = meta['content']
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = BING_URL + img_url
                bg_image = img_url

        if bg_image:
            img_name = os.path.basename(bg_image.split('?')[0])
            img_path = os.path.join(IMAGE_DIR, img_name)
            if not os.path.exists(img_path):
                img_data = requests.get(bg_image, headers=headers, timeout=10).content
                with open(img_path, 'wb') as f:
                    f.write(img_data)
            return f"/static/images/{img_name}", "Today's Bing Wallpaper"
    except Exception as e:
        print(f"[ERROR] {e}")
    return "/static/images/default.jpg", "Bing Wallpaper"

@app.route("/")
def index():
    img_url, title = get_bing_wallpaper()
    return render_template("index.html", img_url=img_url, title=title)

@app.route('/static/images/<filename>')
def download_file(filename):
    return send_from_directory(IMAGE_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)