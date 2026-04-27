import requests
import pandas as pd
import random
from datetime import datetime
import json

import urllib.parse

import os

def fetch_wikipedia_views(article="Songkran", category_name="Outdoor (General)", days=50):
    # Wikipedia REST API for daily pageviews
    # Format: /metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/Songkran/daily/2023030100/2023043000
    headers = {'User-Agent': 'TikTokABM_Research_Agent/1.0 (deepmind)'}
    
    # URL Encode the article name to handle spaces/special characters
    quoted_article = urllib.parse.quote(article)
    
    # We use a 50-day window around a known trend spike for a clean dataset (Songkran season 2023)
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/all-agents/{quoted_article}/daily/2023030100/2023050300"
    
    print(f"Fetching real-world global interest data for '{article}'...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to fetch data: {response.text}")
        # Fallback to simulated data if API fails
        views = [int(1000000 / (1 + 10 * (2.718 ** (-0.2 * (i - 30))))) for i in range(60)]
    else:
        data = response.json()['items']
        # Extract the views and scale them up to TikTok proportions (e.g. 1 wiki view = 50 TikTok views)
        views = [item['views'] * 50 for item in data]
        
    # Cap to exactly 60 steps to match the ABM 60-day trend window
    views = views[:60]
    
    # Generate realistic Sentiment based on the view volume (volume usually correlates with positive hype for products)
    max_views = max(views) if max(views) > 0 else 1
    
    dataset = []
    base_sentiment = 0.4
    for i, v in enumerate(views):
        # Sentiment peaks as views peak, with some random noise mimicking real-world fluctuation
        normalized_hype = v / max_views
        sentiment = base_sentiment + (normalized_hype * 0.4) + random.uniform(-0.05, 0.05)
        sentiment = max(0.0, min(1.0, sentiment)) # Lock between 0 and 1
        
        # New Predictive Connector Metrics
        shares = int(v * random.uniform(0.08, 0.18)) # 8% - 18% share rate
        conversion_rate = round(0.005 + (normalized_hype * 0.015), 4) # 0.5% to 2.0% baseline
        shop_index = round(min(1.0, 0.3 + (normalized_hype * 0.7)), 5)  # Match scraper schema
        
        dataset.append({
            "Tick": i,
            "Date": data[i]['timestamp'][:8] if response.status_code == 200 else f"Day_{i}",
            "Views": v,
            "Sentiment": sentiment,
            "Shares": shares,
            "Conversion_Rate": conversion_rate,
            "Shop_Index": shop_index,
            "Trend_Category": category_name
        })
        
    df = pd.DataFrame(dataset)
    
    # 1. Save generic version for the simulation engine
    df.to_csv("tiktok_trend_data.csv", index=False)
    
    # 2. Save specific archived version for the user
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    safe_name = category_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_")
    archive_path = os.path.join(output_dir, f"trend_data_{safe_name}.csv")
    df.to_csv(archive_path, index=False)
    
    print(f"Successfully generated datasets: 'tiktok_trend_data.csv' and '{archive_path}'!")

if __name__ == "__main__":
    fetch_wikipedia_views()
