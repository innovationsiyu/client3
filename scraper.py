import re
import requests
import time
from yusi_utils import retrieve

SPIDER_API_KEY = retrieve("Spider")


def purify(text):
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r'\s*[!@#]?\[(?:[^\[\]]*\[[^\]]*\][^\[\]]*|[^\[\]]*)\]\([^)]*\)', '', text)
    text = re.sub(r'\s*\[[^\[\]]*\]\([^)]*\)', '', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'^[^A-Za-z0-9\u0080-\uffff]*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'\n+', '\n', text)
    return text[:30000].strip()


def reader(target_url, delay=1):
    url = f"https://r.jina.ai/{target_url}"
    for attempt in range(3):
        try:
            print(f"Sending request to {url}")
            response = requests.get(url, timeout=20)
            if response.text:
                return purify(response.text)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(delay)
                delay *= 2
    print("Failed to get a valid response after maximum retries")
    return None


def spider(target_url, delay=1):
    url = "https://api.spider.cloud/crawl"
    headers = {
        "Authorization": f"Bearer {SPIDER_API_KEY}",
    }
    data = {
        "url": target_url,
        "limit": 1,
        "return_format": "markdown",
    }
    for attempt in range(3):
        try:
            print(f"Sending request to {url}")
            response = requests.post(url, headers=headers, json=data, timeout=20).json()
            content = response[0].get("content")
            if content:
                return purify(content)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(delay)
                delay *= 2
    print("Failed to get a valid response after maximum retries")
    return None


def get_web_text(target_url):
    for index, request in enumerate([reader, spider]):
        try:
            text = request(target_url)
            if text:
                if len(text) >= 500 or index == len([reader, spider]) - 1:
                    return text
        except Exception:
            continue
    return None
