# ============================================
# core/news.py - News Manager Module
# ============================================
"""News fetching module for BingHome"""

import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

class NewsManager:
    def __init__(self):
        self.api_key = os.environ.get('BING_API_KEY', '')
        self.news_cache = []
        self.last_fetch = None
        
    def fetch_news(self, category='general', count=10):
        """Fetch news from Bing News API"""
        if not self.api_key:
            logger.warning("Bing API key not configured")
            return self.news_cache
        
        try:
            headers = {'Ocp-Apim-Subscription-Key': self.api_key}
            params = {
                'mkt': 'en-US',
                'count': count,
                'freshness': 'Day',
                'category': category
            }
            
            response = requests.get(
                'https://api.bing.microsoft.com/v7.0/news',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                self.news_cache = [{
                    'title': article['name'],
                    'description': article.get('description', ''),
                    'url': article['url'],
                    'thumbnail': article.get('image', {}).get('thumbnail', {}).get('contentUrl', ''),
                    'provider': article['provider'][0]['name'] if article.get('provider') else '',
                    'published': article.get('datePublished', ''),
                    'category': category
                } for article in data.get('value', [])]
                
                self.last_fetch = datetime.now()
                logger.info(f"Fetched {len(self.news_cache)} news articles")
                
        except Exception as e:
            logger.error(f"News fetch error: {e}")
        
        return self.news_cache
    
    def get_headlines(self):
        """Get just headlines"""
        return [{'title': item['title'], 'provider': item['provider']} 
                for item in self.news_cache[:5]]
    
    def search_news(self, query):
        """Search for specific news"""
        try:
            headers = {'Ocp-Apim-Subscription-Key': self.api_key}
            params = {
                'q': query,
                'mkt': 'en-US',
                'count': 10
            }
            
            response = requests.get(
                'https://api.bing.microsoft.com/v7.0/news/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('value', [])
                
        except Exception as e:
            logger.error(f"News search error: {e}")
        
        return []
