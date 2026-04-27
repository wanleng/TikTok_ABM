import random
import os
import pandas as pd

class DataEnvironment:
    """
    Simulates the global TikTok environment.
    Ingests real historical data from 'tiktok_trend_data.csv' if available.
    Otherwise, falls back to mathematical curves.
    """
    def __init__(self, csv_path="tiktok_trend_data.csv"):
        self.csv_path = csv_path
        self.has_real_data = False
        self.active_category = "Initializing..."
        
        self.refresh_data()
        
    def refresh_data(self):
        try:
            if os.path.exists(self.csv_path):
                self.df = pd.read_csv(self.csv_path)
                self.has_real_data = True
                self.current_tick = 0
                self.max_ticks = len(self.df) 
                
                # Auto-fix column mapping for high-fidelity scrapers
                # If there's an extra column between Conversion_Rate and Trend_Category
                if len(self.df.columns) > 7 and 'Shop_Index' not in self.df.columns:
                    # Rename the 7th column (index 6) if it's likely the Shop Index
                    cols = list(self.df.columns)
                    cols[6] = 'Shop_Index'
                    self.df.columns = cols

                if 'Trend_Category' in self.df.columns:
                    self.active_category = self.df.iloc[0]['Trend_Category']
                else:
                    self.active_category = "General Trend"
            else:
                self.has_real_data = False
                self.current_tick = 0
                self.max_ticks = 60
                self.active_category = "Simulated Fallback"
        except Exception as e:
            print(f"Error loading CSV {e}, falling back to math simulation.")
            self.has_real_data = False
            self.current_tick = 0
            self.max_ticks = 60
            self.active_category = "Error Fallback"
    
    def get_trend_category(self):
        """Returns the specific category name linked to the active dataset."""
        return self.active_category
    
    def get_current_date(self):
        """Returns the date string for the current tick."""
        import datetime
        if self.has_real_data:
            return str(self.df.iloc[self.current_tick]['Date'])
        
        # Fallback: Start from today's date if no real data
        start_date = datetime.datetime.now()
        current_date = start_date + datetime.timedelta(days=self.current_tick)
        return current_date.strftime("%d.%m.%Y")
    
    def step(self):
        """Advance the environment one tick."""
        if self.current_tick < self.max_ticks - 1:
            self.current_tick += 1
        
    def get_sentiment_score(self):
        if self.has_real_data:
            return float(self.df.iloc[self.current_tick]['Sentiment'])
            
        # Fallback Math Simulation
        base_sentiment = 0.3
        trend_peak = self.max_ticks / 2
        trend_factor = 0.6 * (1.0 - ((self.current_tick - trend_peak) / trend_peak) ** 2)
        trend_factor = max(0, trend_factor)
        noise = random.uniform(-0.1, 0.1)
        score = base_sentiment + trend_factor + noise
        return max(0.0, min(1.0, score))
        
    def get_global_views(self):
        if self.has_real_data:
            return int(self.df.iloc[self.current_tick]['Views'])
            
        # Fallback Math Simulation
        L = 1000000  # max views
        k = 0.2      # steepness
        x0 = self.max_ticks / 2 # midpoint
        views = L / (1 + (L * 0.001) * (2.71828 ** (-k * (self.current_tick - x0))))
        return int(views)

    def get_view_divisor(self):
        """Returns a scaling factor for reach calculation based on data volume."""
        if self.has_real_data:
            max_v = self.df['Views'].max()
            # We want the peak of the trend to roughly equal a 1.0-2.0 reach score
            return max(1000, max_v / 2.0)
        return 500000.0 # Default for 1M max fallback simulation
    
    def get_shares(self):
        if self.has_real_data and 'Shares' in self.df.columns:
            return int(self.df.iloc[self.current_tick]['Shares'])
        
        # Fallback: 10% of views
        return int(self.get_global_views() * 0.1)

    def get_shop_index(self):
        if self.has_real_data and 'Shop_Index' in self.df.columns:
            return float(self.df.iloc[self.current_tick]['Shop_Index'])
        return 0.2 # Default baseline

    def get_conversion_rate(self):
        if self.has_real_data and 'Conversion_Rate' in self.df.columns:
            return float(self.df.iloc[self.current_tick]['Conversion_Rate'])
            
        # Fallback: Base 1%
        return 0.01
