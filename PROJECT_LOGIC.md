# Technical Documentation: TikTok Trend Diffusion ABM

## 1. System Overview

The **"Social Commerce Dynamics: TikTok Trend Diffusion"** project models a **Human-Environment System** where the global TikTok feed acts as a dynamic external environment and the individual consumers act as autonomous agents. The model is calibrated for the **Songkran festival** (Thai New Year, April 13-15), simulating a 60-day pre-Songkran shopping buildup from **March 1 → April 30**.

In this system:
- **Environment (The Feed):** Dictates macro-level variables over time such as the aggregated **Sentiment Score** of a trending hashtag, the total **View Counts** indicating the trend's velocity, **Conversion Rate**, and **Shop Index** for TikTok Shop activity.
- **Agents (The Consumers):** Autonomous entities placed within a **Watts-Strogatz small-world** social network topology. They observe both the global environmental signals (TikTok feed) and local social signals (peer purchases) to make state transitions through a marketing funnel.

### Architecture Diagram (TikTok-Net 5-4-3)

The system maps to a deep learning pipeline with 3 layers:

| Layer | Nodes | Description |
| :--- | :--- | :--- |
| **Input (5)** | Views, Sentiment, Shares, Conversion Rate, Shop Index | Environment signals from `tiktok_trend_data.csv` |
| **Hidden (4)** | Awareness, Interest, Deliberation, Purchase Probability | Agent cognitive stages (internal state transitions) |
| **Output (3)** | Purchases, Revenue (GMV), Net Commission | Emergent economic outcomes |

## 2. Data Sources

The system supports two data ingestion pipelines, selectable from the UI:

### 2.1 TikTok Scraper (Primary — `tiktok_scraper.py`)

Uses **Selenium** with stealth settings to scrape real TikTok search results. For each product category, the scraper executes a **3-tier search strategy**:

1. **Tier 1 — Thai Hashtags** (highest relevance): e.g., `#ปืนฉีดน้ำ #สงกรานต์`
2. **Tier 2 — English + Songkran**: e.g., `water gun Songkran TikTok Shop`
3. **Tier 3 — Broad Fallback**: e.g., `water gun Songkran`

All 12 product categories have pre-mapped Thai/English query pairs in `songkran_queries`.

**Synthesis Pipeline (6 Optimizations):**

Cross-sectional scraped samples are mapped to a 60-day time-series using:

1. **Sigmoid Index Mapping** — Logistic function $\sigma(t) = \frac{1}{1 + e^{-0.12(t - 35)}}$ centers inflection at Day 35 (Songkran approach).
2. **Dynamic Conversion Rate** — $CR(t) = 0.005 + \left(\frac{V_{views}(t)}{V_{max}} \cdot 0.015\right)$, ranging from 0.5% to 2.0%.
3. **Cyclical Noise** — Normal distribution $\mathcal{N}(1.0, 0.08)$ with 10% weekend boost ($\text{day\_of\_week} \geq 5$).
4. **Deduplication** — `seen_likes` set prevents counting the same video twice.
5. **Tiered View Ratios** — View-to-like multiplier varies by virality: 30× (niche), 45× (popular), 60× (viral >100K likes).
6. **Normalized Shop Index** — $\text{Shop\_Index}(t) = \min(1.0,\ 0.3 + \frac{L(t)}{L_{max}} \cdot 0.7)$, smooth ramp across sample range.

**Date Range:** Hardcoded to Songkran period: `datetime(2024, 3, 1)` → 60 days → April 30.

### 2.2 Wikipedia Proxy (Fallback — `fetch_real_data.py`)

Uses the **Wikimedia REST API** to fetch daily pageview counts for related articles (e.g., "Songkran", "Sunscreen"). Scales Wikipedia views by 50× to approximate TikTok proportions. Used as a demo/fallback data source.

### CSV Schema (`tiktok_trend_data.csv`)

| Column | Type | Source |
| :--- | :--- | :--- |
| `Tick` | int | Row index (1-60) |
| `Date` | string | `YYYY-MM-DD` format |
| `Views` | int | Projected view count |
| `Sentiment` | float | 0.0 - 1.0 normalized sentiment |
| `Shares` | int | Projected share/repost count |
| `Conversion_Rate` | float | Dynamic CR (0.005 - 0.020) |
| `Shop_Index` | float | TikTok Shop activity signal (0.3 - 1.0) |
| `Trend_Category` | string | Product name (e.g., "Water Gun") |

## 3. Agent Logic & Attributes

Agents transition through a **4-state marketing funnel** (3 transitions):

1. **Unaware (Gray):** Baseline state — agent has not encountered the trend.
2. **Aware (Cyan):** Agent has been reached by the trend (driven by views, shares, network).
3. **Interested (Yellow):** Agent has evaluated sentiment and social proof, deliberating purchase.
4. **Purchased (Green):** Terminal state — agent has adopted the trend/product.

### Agent Types

| Type | $P_{base}$ | $T_{purchase}$ | $T_{interest}$ | Behavior |
| :--- | :--- | :--- | :--- | :--- |
| **Innovator** | 0.9 | 0.3 | 0.2 | Eager early adopters. Rely on raw sentiment, low social proof needed. |
| **Follower** | 0.6 | 0.5 | 0.4 | Social-proof driven. Intent scales with global views and neighbor purchases. |
| **Skeptic** | 0.3 | 0.8 | 0.7 | Highly resistant. Requires sustained high sentiment ($S > 0.65$ for $t \geq 4$ ticks) before entering funnel. |

### Default Agent Mix

- 10% Innovators, 70% Followers, 20% Skeptics (configurable via UI sliders)

## 4. Mathematical Framework

### 4.1 Environmental Variables

At every tick $t$, the `DataEnvironment` provides:
- $S(t)$: Global Sentiment Score ($0 \le S \le 1$).
- $V_{views}(t)$: Global Views.
- $V_{shares}(t)$: Global Shares/Reposts.
- $CR_{base}(t)$: Baseline Conversion Rate.
- $SI(t)$: TikTok Shop Index ($0 \le SI \le 1$).

The **View Divisor** $D$ is dynamically calculated as $D = \max(1000, V_{max} / 2)$, ensuring the reach score normalizes correctly regardless of data scale.

### 4.2 Transition 1: Unaware → Aware

Driven by **Reach Score**:
$$Reach\_Score_i(t) = \frac{V_{views}(t)}{D} + \frac{V_{shares}(t)}{D \cdot 0.1} \cdot \alpha_{viral} + \left(0.4 \cdot \frac{N_{aware, i}}{N_{total, i}}\right)$$

Where $\alpha_{viral}$ is the **Fashion Category Viral Multiplier** (default 1.0, set to 2.0 for Fashion items).

If $Reach\_Score_i(t) > T_{aware, i} \times 0.2$, state → *Aware*.

### 4.3 Transition 2: Aware → Interested

Driven by **Deliberation** (requires sustained sentiment):

The agent's `deliberation_ticks` counter increments when $S(t) > T_{interest, i}$. If sentiment drops, the counter decrements (cold feet). After **2 consecutive qualifying ticks**, the agent transitions to *Interested* and **stops for that tick** (no instant purchase).

### 4.4 Transition 3: Interested → Purchased

Driven by the **Market Volatility Equation**, **Conversion Baseline**, and **TikTok Shop Impulse**.

**Step 1: Calculate Intent**
$$I_i(t) = \left(S(t) \cdot \mu_{sentiment} \cdot P_{base, i}\right) + \left(0.5 \cdot \frac{N_{purchased, i}(t)}{N_{total, i}}\right) + \beta_{trend}$$

Where:
- $\mu_{sentiment}$ is the user-configurable **Sentiment Multiplier** (UI slider)
- $\beta_{trend}$ is the **Trend Context Intent Boost** (Outdoor: +0.25, others: 0)
- Followers additionally add a view factor: $\min(0.4, \frac{V_{views}}{D} \cdot 0.4)$

**Step 2: Impulse Decay**
$$Impulse\_Factor(t) = 2.5 \times e^{-0.02 \cdot t}$$

This models buying fatigue: 2.5× at Day 0 → ~0.75× by Day 60.

**Step 3: Shop Boost**
$$Shop\_Boost = SI(t) \times 3.0$$

**Step 4: Final Probability (with market volatility)**
$$Base\_Prob = \left(CR_{base}(t) \times 2 + I_i(t) \times 0.5\right) \times Impulse\_Factor(t) \times (1 + Shop\_Boost)$$
$$Final\_Prob_i(t) = Base\_Prob \times (1 - \sigma) + (\sigma \times \epsilon)$$

Where $\sigma$ is the **Market Volatility** (randomness slider, 0=deterministic, 1=random) and $\epsilon \sim U(0,1)$.

If $Final\_Prob_i(t) \geq T_{purchase, i}$, state → *Purchased*.

## 5. Category-Specific Logic Buffs

The simulation applies specialized mathematical "Buffs" based on the selected Trend Context:

| Context | Target | Buff | Rationale |
| :--- | :--- | :--- | :--- |
| **Beauty** (Sunscreen, Makeup, Mist) | Innovators | $P_{base} +0.15$, $T_{purchase} -0.1$ | Early adopters react to aesthetic/protective features |
| **Tech** (Case, Camera, Speaker) | Skeptics | Wait threshold: $4 \to 2$ | Skeptics won over by immediate utility/durability |
| **Fashion** (Shirt, Shorts, Sandal) | Global Reach | $\alpha_{viral} = 2.0$ | Visual fashion spreads 2× faster via shares |
| **Outdoor** (Gun, Bucket, Ticket) | Followers | $\beta_{trend} = +0.25$ | High seasonal demand drives mass-market majority |

## 6. Financial Forecasting (TikTok Shop)

When TikTok Shop is enabled via UI toggle:

- **Gross Merchandise Value:** $GMV = \text{Total\_Purchases} \times \text{Price}$
- **Net Commission:** $Revenue = GMV \times \frac{Comm\%}{100}$

Both are tracked per-tick by the `DataCollector` and displayed in the Revenue Projection chart.

## 7. Algorithm Description

### 7.1 The Simulation Loop (`model.step()`)

At every tick $t$:

1. **Data Collection** — `DataCollector` snapshots all metrics (before agent mutations):
   - Model reporters: `Date`, `Total Aware`, `Total Interested`, `Total Purchased`, `Sentiment Score`, `Global Views`, `Shares`, `Shop GMV`, `Net Commission`
   - Agent reporters: `is_aware`, `is_interested`, `purchased`
2. **Environment Advance** — `DataEnvironment.step()` increments `current_tick`, advancing to the next row of `tiktok_trend_data.csv`.
3. **Agent Shuffle & Execute** — `agents.shuffle_do("step")` randomizes evaluation order and executes each agent's funnel logic.

### 7.2 Network Topology

Agents are placed on a **Watts-Strogatz small-world graph** (`nx.watts_strogatz_graph(n, k=4, p=0.1)`):
- `k=4`: Each agent connects to 4 nearest neighbors
- `p=0.1`: 10% rewiring probability creates long-range shortcuts
- This topology models real social networks: high clustering + short average path length

### 7.3 Stochastic Components

1. **Network Initialization** — Rewiring probability `p=0.1` creates random long-range edges.
2. **Agent Scheduling** — `shuffle_do("step")` randomizes evaluation order each tick.
3. **Market Volatility** — $\sigma$ parameter adds stochastic noise to purchase decisions.
4. **Data Noise** — Scraper applies $\mathcal{N}(1.0, 0.08)$ + weekend boost to synthesized data.

## 8. Predictive Model Evaluation

The UI implements a rolling velocity forecast to estimate market saturation:

### Velocity Calculation (Diff-Based)
$$R(t) = \frac{Purchases(t) - Purchases(t - w)}{w}$$
Where $w = \min(5, \text{available\_ticks})$.

### ETA Forecast
$$ETA = \min\left(t + \frac{M_{remaining}}{R(t)},\ T_{max} + 30\right)$$
Capped at $T_{max} + 30$ (≈90 days) to prevent unrealistic projections.

### Reliability Score (Coefficient of Variation)
Uses the last 15 ticks of purchase diffs (positive only):
$$CV = \frac{\sigma_{diffs}}{\mu_{diffs}}$$
$$Reliability = \max\left(0,\ \min\left(100,\ 100 \times (1 - \min(1, CV))\right)\right)$$

- $CV = 0$ → 100% reliability (perfectly stable velocity)
- $CV \geq 1$ → 0% reliability (erratic/unstable)
- Near-saturation (>90%) auto-assigns 95% reliability.

### R² Goodness-of-Fit
A logistic growth curve is fitted to the actual purchase data:
$$Predicted = \frac{N}{1 + e^{-k(t - t_0)}}$$
$$R^2 = 1 - \frac{\sum (y_{actual} - y_{pred})^2}{\sum (y_{actual} - \mu_{actual})^2}$$

- $R^2 > 0.90$ → Excellent fit, adoption follows classic S-curve.
- $R^2 > 0.70$ → Good fit with some noise.
- $R^2 < 0.70$ → Adoption deviates from ideal pattern.

## 9. Output Files

### `simulation_results.csv` (via `run.py`)

| Column | Description |
| :--- | :--- |
| `Tick` | Time step index |
| `Date` | Calendar date from environment |
| `Total Aware` | Cumulative agents in Aware state |
| `Total Interested` | Cumulative agents in Interested state |
| `Total Purchased` | Cumulative agents in Purchased state |
| `Sentiment Score` | Environment sentiment at tick |
| `Global Views` | Environment views at tick |
| `Shares` | Environment shares at tick |
| `Shop GMV` | Gross revenue (Purchases × Price) |
| `Net Commission` | Platform commission (GMV × Comm%) |
| `Trend_Category` | Active product category name |

### `agent_type_analysis.csv` (via `run.py`)

Outputs agent-level analysis showing which agent types (Innovator, Follower, Skeptic) purchased when, their conversion rate, average purchase tick, earliest and latest purchase ticks.

### `scenario_comparison.csv` (via `run.py`)

Outputs a comparison report across 4 scenarios: 500 agents Shop ON, 500 agents Shop OFF, 100 agents Shop ON, and 1000 agents Shop ON.

### Visualizations (via `run.py`)

- `trend_diffusion.png`: Dual-axis plot of Purchases vs Sentiment + Scaled Views.
- `scenario_comparison.png`: Line chart overlaying market penetration across multiple scenarios over time.

## 10. Metrics for Analysis

The extracted `.csv` files support both descriptive and inferential statistical methods:

- **Volume Trajectory (Purchases over Time):** Evaluated against standard S-Curve diffusion of innovation models.
- **Correlation Matrix:** Heatmap of Sentiment Score ↔ Global Views ↔ Total Purchased ↔ Net Commission (displayed live in UI).
- **Trend Convergence Rate:** The derivative $\frac{dP}{dt}$ — how quickly initial hype cascades into network-wide adoption.
- **Agent Sub-class Performance:** Aggregate buying volumes by Innovator/Follower/Skeptic for targeted hypothesis testing.
- **Network Centrality Yield:** (Future) Cross-referencing graph centrality vs purchase tick to evaluate influence node effects.

## 11. UI Components (Solara Dashboard)

The dashboard (`ui.py`) provides three tab views:

| Tab | Components |
| :--- | :--- |
| **Analytics Dashboard** | Conversion Funnel chart, Viral Engagement Velocity, Revenue Projection, Correlation Matrix, Predictive Evaluation |
| **Social Network Graph** | Live Plotly network visualization with color-coded agent states (Gray → Cyan → Yellow → Green) |
| **System Architecture (DL Mapping)** | TikTok-Net 5-4-3 neural network diagram with live-pulsing node sizes and activation-weighted edges |

**Live Stats Panel** (always visible): Sentiment, Market Aware, Conversions, Projected GMV.

**Calibration Panel** (sidebar): Trend Context selector, Agent count, Sentiment Impact, Influence Reach, Tick Interval, TikTok Shop toggle with Price/Commission sliders.
