# TikTok Trend Diffusion ABM

**Social Commerce Dynamics: Modeling TikTok Trend Adoption During Songkran Festival**

An Agent-Based Model (ABM) that simulates how TikTok viral trends convert into real consumer purchases during Thailand's Songkran festival period. Built with real scraped TikTok data, a 3-stage marketing funnel, and deep learning architecture mapping.

---

## Overview

This project models a **human-environment system** where:
- **Environment** → TikTok's trending feed (real scraped data driving views, sentiment, shares)
- **Agents** → 500 virtual consumers on a Watts-Strogatz small-world social network
- **Interaction** → Agents observe global trend signals + local peer behavior to transition through a marketing funnel: **Unaware → Aware → Interested → Purchased**

The simulation covers a **60-day window** (March 1 – April 30) across 12 Songkran product categories in 4 segments: Beauty, Tech, Fashion, and Outdoor.

### Key Features

- **Real TikTok data** scraped via Selenium with stealth configuration
- **3-stage marketing funnel** with deliberation mechanics (not binary buy/don't-buy)
- **3 agent personality types**: Innovator (10%), Follower (70%), Skeptic (20%)
- **Category-specific behavioral buffs** (Fashion spreads 2× faster, Outdoor gets seasonal FOMO boost)
- **TikTok Shop financial model** with GMV and commission tracking
- **Deep learning mapping** (TikTok-Net 5-4-3 architecture)
- **Interactive dashboard** with real-time charts, network visualization, and predictive analytics
- **Multi-scenario comparison** and agent-level purchase timing analysis

---

## Project Structure

```
TikTok_ABM/
├── agents.py             # Agent classes (Innovator, Follower, Skeptic) with funnel logic
├── model.py              # Mesa model with DataCollector and network initialization
├── environment.py        # DataEnvironment that loads and serves CSV trend data
├── tiktok_scraper.py     # Selenium-based TikTok data scraper
├── fetch_real_data.py    # Wikipedia API fallback data source
├── run.py                # Headless batch runner with multi-scenario comparison
├── ui.py                 # Solara + Plotly interactive dashboard
├── app.py                # Mesa visualization (legacy)
├── requirements.txt      # Python dependencies
├── tiktok_trend_data.csv # Scraped trend data (60 days)
├── PROJECT_LOGIC.md      # Technical documentation of all math and logic
└── output/               # Auto-generated CSV results and charts
    ├── simulation_results.csv
    ├── agent_type_analysis.csv
    ├── scenario_comparison.csv
    ├── trend_diffusion.png
    └── scenario_comparison.png
```

---

## Installation

### Prerequisites
- Python 3.9+
- Google Chrome (for TikTok scraping)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/wanleng/TikTok_ABM.git
cd TikTok_ABM

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## Usage

### Option 1: Headless Simulation (No UI)

```bash
python run.py
```

Runs 4 scenarios automatically (500 agents Shop ON/OFF, 100 agents, 1000 agents) and exports all results to the `output/` folder.

### Option 2: Interactive Dashboard

```bash
solara run ui.py
```

Opens a web browser at `http://localhost:8765` with the full interactive dashboard featuring:
- **Analytics Dashboard** — Conversion funnel, viral engagement, revenue projection, correlation matrix
- **Social Network Graph** — Live network visualization with color-coded agent states
- **System Architecture** — TikTok-Net 5-4-3 deep learning mapping with live activation

### Option 3: Scrape Fresh TikTok Data

```bash
python tiktok_scraper.py
```

Scrapes real TikTok data for the configured product category and generates a new `tiktok_trend_data.csv`.

---

## How It Works

### Agent Decision Pipeline

Each tick, every agent evaluates three potential state transitions:

1. **Unaware → Aware**: Driven by a **Reach Score** combining global views, shares, and network neighbor awareness
2. **Aware → Interested**: Requires **2 consecutive ticks** of positive sentiment above the agent's threshold (deliberation mechanic)
3. **Interested → Purchased**: Uses the **Market Volatility Equation** combining intent, impulse decay, TikTok Shop boost, and stochastic noise

### Category Buffs

| Category | Target | Effect |
|----------|--------|--------|
| Beauty (Sunscreen, Makeup) | Innovators | +0.15 base probability, −0.1 threshold |
| Tech (Case, Camera) | Skeptics | Wait threshold: 4 → 2 ticks |
| Fashion (Shirt, Shorts) | Global | 2× viral share multiplier |
| Outdoor (Water Gun, Bucket) | Followers | +0.25 trend intent boost |

### Deep Learning Mapping (TikTok-Net 5-4-3)

The ABM maps to a neural network architecture:

| Layer | Nodes | Description |
|-------|-------|-------------|
| Input (5) | Views, Sentiment, Shares, Conversion Rate, Shop Index | Environment signals |
| Hidden (4) | Awareness, Interest, Deliberation, Purchase Probability | Agent cognitive states |
| Output (3) | Purchases, Revenue (GMV), Net Commission | Economic outcomes |

---

## Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent Framework | [Mesa](https://github.com/projectmesa/mesa) | Agent scheduling, data collection |
| Social Network | [NetworkX](https://networkx.org/) | Watts-Strogatz small-world graph |
| Data Scraping | [Selenium](https://www.selenium.dev/) + Stealth | Real TikTok trend data |
| Dashboard | [Solara](https://solara.dev/) + [Plotly](https://plotly.com/) | Interactive visualization |
| Data Analysis | [Pandas](https://pandas.pydata.org/) + [NumPy](https://numpy.org/) | Statistical analysis |
| Fallback Data | Wikipedia REST API | Pageview-based proxy data |

---

## Sample Results

Running 500 agents for 60 ticks with the "Songkran Shirt" category:

| Metric | Value |
|--------|-------|
| Market Penetration | 92.0% (460/500 agents) |
| Views → Purchases Correlation | r = 0.755 |
| Sentiment → Purchases Correlation | r = 0.611 |
| Projected GMV | ฿137,540 |
| Net Commission (10%) | ฿13,754 |

---

## License

This project was developed as an undergraduate coursework for the **Data Analytics in Agent-Based Modeling** module.

---

## Author

**Sai Swam Wan Hline**
