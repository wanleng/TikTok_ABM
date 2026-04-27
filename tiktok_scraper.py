import time
import json
import os
import pandas as pd
import urllib.parse
import numpy as np
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth
from selenium.webdriver.common.by import By

def setup_stealth_driver(headless=False):
    """Configures Chrome with professional stealth settings."""
    options = Options()
    if headless: options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--window-size=1920,1080")
    # Add common user agent
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
    return driver

def parse_count(text):
    if not text: return 0
    text = text.upper().replace(' ', '').replace(',', '')
    try:
        if 'M' in text: return int(float(text.replace('M', '')) * 1_000_000)
        if 'K' in text: return int(float(text.replace('K', '')) * 1_000)
        return int(text)
    except: return 0

def dismiss_modals(driver):
    try:
        close_selectors = ['[aria-label="Close"]', 'div[class*="ButtonClose"]', 'div[data-e2e="close-icon"]']
        for sel in close_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                if el.is_displayed():
                    el.click()
                    return True
    except: pass
    return False

def scrape_tiktok_trends(category_name, keyword, depth=100):
    """
    Scrapes TikTok content for Songkran-period trending products.
    Searches use Thai + English terms targeting the pre-Songkran shopping
    season (March-April) to capture the viral buildup curve.
    """
    driver = setup_stealth_driver(headless=False)
    video_units = []
    
    # Audit-based selectors
    selectors = [
        'div.e1wv0r560', # Latest video container
        'div[data-e2e="search_video-item"]',
        'div[class*="DivContainer"][role="button"]',
        'div[aria-label="Watch in full screen"]'
    ]

    # Songkran-specific search terms per category (Thai + English, tiered)
    songkran_queries = {
        "Water Gun":         ["#ปืนฉีดน้ำ #สงกรานต์",     "water gun Songkran TikTok Shop",   "water gun Songkran"],
        "Water Bucket":      ["#ถังน้ำสงกรานต์",           "water bucket Songkran",            "water bucket"],
        "S2O Ticket":        ["#S2O #สงกรานต์",            "S2O Songkran festival ticket",     "S2O festival"],
        "Songkran Shirt":    ["#เสื้อสงกรานต์ #เสื้อลายดอก", "Songkran Hawaiian shirt",          "Songkran shirt"],
        "Dry Shorts":        ["#กางเกงขาสั้น #สงกรานต์",    "dry fit shorts Songkran",          "waterproof shorts"],
        "Sandals":           ["#รองเท้าสงกรานต์",           "sandals Songkran waterproof",      "waterproof sandals"],
        "Sunscreen":         ["#กันแดด #สงกรานต์",          "sunscreen Songkran waterproof",    "sunscreen SPF50"],
        "Makeup":            ["#เมคอัพกันน้ำ #สงกรานต์",     "waterproof makeup Songkran",       "waterproof makeup"],
        "Cooling Mist":      ["#สเปรย์เย็น #สงกรานต์",      "cooling mist spray Songkran",      "cooling mist spray"],
        "Waterproof Case":   ["#ซองกันน้ำ #สงกรานต์",       "waterproof phone case Songkran",   "waterproof phone case"],
        "Action Camera":     ["#กล้องกันน้ำ #สงกรานต์",      "GoPro Songkran waterproof",        "action camera waterproof"],
        "Bluetooth Speaker": ["#ลำโพงกันน้ำ #สงกรานต์",     "waterproof speaker Songkran",      "waterproof bluetooth speaker"],
    }

    # Get category-specific queries or fallback to generic Songkran terms
    queries = songkran_queries.get(category_name, [
        f"#{keyword.replace(' ', '')} #สงกรานต์",
        f"{keyword} Songkran TikTok Shop",
        f"{keyword}"
    ])

    try:
        for i, q in enumerate(queries):
            print(f"[{i+1}/{len(queries)}] Searching: '{q}'...")
            encoded_q = urllib.parse.quote_plus(q)
            url = f"https://www.tiktok.com/search?q={encoded_q}&sort_type=1"
            
            driver.get(url)
            time.sleep(8)
            dismiss_modals(driver)
            
            # Check for immediate results
            for sel in selectors:
                video_units = driver.find_elements(By.CSS_SELECTOR, sel)
                if len(video_units) > 3: break
            
            if len(video_units) > 3:
                print(f"✅ Success on Attempt {i+1}!")
                break
            else:
                print(f"⚠️ Attempt {i+1} yielded no results.")

        if not video_units:
            print("❌ Critical: All search attempts yielded 0 results.")
            return False

        # Accumulate more results
        scroll_count = 10
        for s in range(scroll_count):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            print(f"  - Accumulating viral samples... {s+1}/{scroll_count}")
            time.sleep(3)
            if s % 3 == 0: dismiss_modals(driver)
            
        print("📊 TIERED SCRAPING: Identifying viral outliers...")
        
        # Re-fetch units after scrolls
        for sel in selectors:
            video_units = driver.find_elements(By.CSS_SELECTOR, sel)
            if len(video_units) > 10: break

        if not video_units:
            print("❌ Critical: All scraping attempts failed.")
            return False

        raw_samples = []
        seen_likes = set()  # Fix #4: Deduplication
        for unit in video_units:
            try:
                # Target the Strong counts which are usually views or likes
                stat_elements = unit.find_elements(By.TAG_NAME, 'strong')
                if not stat_elements: continue
                
                # First strong is usually the count shown on card (Likes or Views)
                likes = parse_count(stat_elements[0].text)
                if likes < 5: continue
                if likes in seen_likes: continue  # Fix #4: Skip duplicates
                seen_likes.add(likes)
                
                # Fix #5: Tiered view projection (viral content has higher view/like ratio)
                if likes > 100000:
                    view_ratio = 60  # Viral: higher view-to-like ratio
                elif likes > 10000:
                    view_ratio = 45  # Popular
                else:
                    view_ratio = 30  # Niche/emerging
                
                raw_samples.append({
                    "likes": likes,
                    "views": likes * view_ratio,
                    "sentiment": min(1.0, (likes / 50000) * 0.2 + 0.6),
                    "shares": int(likes * 0.12)
                })
            except: continue

        if len(raw_samples) < 3: 
            print("Insufficient high-quality samples found.")
            return False
        
        # --- RISING TREND SYNTHESIS (60 DAYS) ---
        raw_samples.sort(key=lambda x: x['likes'])
        n_samples = len(raw_samples)
        
        # Fix #6: Compute sample-level normalization for Shop_Index and CR
        max_likes = max(s['likes'] for s in raw_samples)
        max_views = max(s['views'] for s in raw_samples)
        
        dataset = []
        # Songkran period: March 1 → April 30 (60-day pre-Songkran buildup)
        base_date = datetime(2024, 3, 1)
        
        for t in range(1, 61):
            # Fix #2: Proper sigmoid mapping using logistic function
            # Centers the inflection point at day 35 with steepness k=0.12
            sigmoid_progress = 1.0 / (1.0 + np.exp(-0.12 * (t - 35)))
            idx = int(sigmoid_progress * (n_samples - 1))
            idx = max(0, min(n_samples - 1, idx))
            sample = raw_samples[idx]
            
            # Fix #3: Normal distribution noise + weekday/weekend pattern
            base_noise = np.random.normal(1.0, 0.08)  # ~8% daily volatility
            day_of_week = (t % 7)  # 0=Mon ... 6=Sun
            weekend_boost = 1.10 if day_of_week >= 5 else 1.0  # 10% weekend lift
            noise = max(0.75, min(1.25, base_noise * weekend_boost))
            
            # Fix #1: Dynamic Conversion_Rate (normalized across sample range)
            normalized_views = sample['views'] / max(1, max_views)
            dynamic_cr = 0.005 + (normalized_views * 0.015)  # 0.5% base → 2.0% peak
            
            # Fix #6: Normalized Shop_Index (smooth ramp across sample range)
            normalized_likes = sample['likes'] / max(1, max_likes)
            dynamic_shop = min(1.0, 0.3 + (normalized_likes * 0.7))
            
            dataset.append({
                "Tick": t,
                "Date": (base_date + timedelta(days=t)).strftime("%Y-%m-%d"),
                "Views": int(sample['views'] * noise),
                "Sentiment": max(0.4, min(1.0, sample['sentiment'] * noise)),
                "Shares": int(sample['shares'] * noise),
                "Conversion_Rate": round(dynamic_cr, 6),
                "Shop_Index": round(dynamic_shop, 5),
                "Trend_Category": category_name
            })

        # Save results
        df = pd.DataFrame(dataset)
        df.to_csv("tiktok_trend_data.csv", index=False)
        print(f"🎊 Rising Trend Synthesis Complete! {len(dataset)} ticks generated.")
        return True
        
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_tiktok_trends("Water Gun", "Water Gun")
