import solara
import solara.lab
import warnings
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import pandas as pd
import math
import time

from model import TikTokModel
from fetch_real_data import fetch_wikipedia_views
from tiktok_scraper import scrape_tiktok_trends

# Categories mapping
TREND_CATEGORIES = [
    "--- Beauty ---",
    "Sunscreen", "Makeup", "Cooling Mist",
    "--- Tech ---",
    "Waterproof Case", "Action Camera", "Bluetooth Speaker",
    "--- Fashion ---",
    "Songkran Shirt", "Dry Shorts", "Sandals",
    "--- Outdoor ---",
    "Water Gun", "Water Bucket", "S2O Ticket"
]

def get_wiki_keyword(selection):
    """Maps UI selection to search terms for both Wikipedia and TikTok."""
    sel = selection.lower()
    # Search Term Mapping
    if any(k in sel for k in ["sunscreen", "makeup", "mist"]):
        return "Sunscreen"
    if any(k in sel for k in ["case", "camera", "speaker", "gopro"]):
        return "Action camera"
    if any(k in sel for k in ["shirt", "shorts", "sandal", "floral"]):
        return "Songkran shirt"
    if any(k in sel for k in ["gun", "bucket", "water"]):
        return "Water gun"
    if any(k in sel for k in ["fest", "ticket", "s2o"]):
        return "S2O Festival"
    return "Songkran"

trend_category = solara.reactive("")

# Agent Mix
n_agents = solara.reactive(150)
prob_innovator = solara.reactive(0.1)
prob_follower = solara.reactive(0.7)
prob_skeptic = solara.reactive(0.2)

# Environmental Controls
sentiment_multiplier = solara.reactive(1.0)
influence_radius = solara.reactive(1)
market_volatility = solara.reactive(0.1)
simulation_speed = solara.reactive(0.5) # Speed control in seconds

# TikTok Shop Controls
use_tiktok_shop = solara.reactive(True)
shop_price = solara.reactive(299)
shop_commission = solara.reactive(10.0)

# Model State
model_instance = solara.reactive(None)
simulation_running = solara.reactive(False)
current_step = solara.reactive(0)
is_fetching = solara.reactive(False)

def init_model(*args):
    is_fetching.value = False
    category = trend_category.value
    if category.startswith("---"): return

    model_instance.value = TikTokModel(
        n_agents=n_agents.value,
        prob_innovator=prob_innovator.value,
        prob_follower=prob_follower.value,
        prob_skeptic=prob_skeptic.value,
        avg_node_degree=4,
        sentiment_multiplier=sentiment_multiplier.value,
        influence_radius=influence_radius.value,
        randomness=market_volatility.value,
        trend_category=category,
        use_tiktok_shop=use_tiktok_shop.value,
        shop_price=shop_price.value,
        shop_commission=shop_commission.value
    )
    current_step.value = 0
    simulation_running.value = False

def refresh_data():
    """Fetch data from Wikipedia pageviews API (proxy/fallback source)."""
    is_fetching.value = True
    try:
        keyword = get_wiki_keyword(trend_category.value)
        fetch_wikipedia_views(article=keyword, category_name=trend_category.value)
        if model_instance.value is not None:
            model_instance.value.env.refresh_data()
        init_model()
    finally:
        is_fetching.value = False

def deep_scrape_data():
    """Scrape real TikTok data via Selenium (primary source, requires Chrome)."""
    is_fetching.value = True
    try:
        success = scrape_tiktok_trends(category_name=trend_category.value, keyword=trend_category.value, depth=50)
        if success:
            if model_instance.value is not None:
                model_instance.value.env.refresh_data()
            init_model()
    finally:
        is_fetching.value = False
        
def run_simulation_loop(cancel):
    while not cancel.is_set():
        if simulation_running.value and model_instance.value is not None:
            # Use step counter (not env.current_tick) to avoid off-by-one:
            # model.step() collects THEN advances, so we need max_ticks iterations
            if current_step.value < model_instance.value.env.max_ticks:
                model_instance.value.step()
                current_step.set(current_step.value + 1)
            else:
                simulation_running.set(False)
        time.sleep(simulation_speed.value)

@solara.component
def AgentNetworkView():
    is_dark = solara.lab.use_dark_effective()
    model = model_instance.value
    step_val = current_step.value # Localize for dependency

    def make_network_fig():
        if model is None: return go.Figure()
        G = model.G
        # Cache layout on model to avoid expensive recomputation every tick
        if not hasattr(model, '_cached_layout'):
            model._cached_layout = nx.spring_layout(G, seed=42)
        pos = model._cached_layout
        
        edge_x, edge_y = [], []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

        edge_trace = go.Scatter(x=edge_x, y=edge_y, line=dict(width=0.5, color='#444' if is_dark else '#bbb'), hoverinfo='none', mode='lines')

        node_x, node_y, node_color = [], [], []
        for node in G.nodes():
            node_x.append(pos[node][0])
            node_y.append(pos[node][1])
            agents = model.grid.get_cell_list_contents([node])
            if not agents: 
                node_color.append("gray")
                continue
            a = agents[0]
            if a.purchased: node_color.append("green")
            elif a.is_interested: node_color.append("yellow")
            elif a.is_aware: node_color.append("cyan")
            else: node_color.append("gray")

        node_trace = go.Scatter(x=node_x, y=node_y, mode='markers', marker=dict(color=node_color, size=10, line_width=2, line_color='white' if is_dark else 'black'))
        return go.Figure(data=[edge_trace, node_trace], layout=go.Layout(showlegend=False, xaxis=dict(showgrid=False, zeroline=False, showticklabels=False), yaxis=dict(showgrid=False, zeroline=False, showticklabels=False), margin=dict(b=0,l=0,r=0,t=0)))

    fig = solara.use_memo(make_network_fig, dependencies=[step_val, is_dark, model])
    
    if model is None:
        return solara.Text("Initialize model to view network")
    
    with solara.Column():
        solara.FigurePlotly(fig)
        # Legend Row
        with solara.Row(justify="center", gap="20px", margin="10px"):
            with solara.Row(gap="5px"):
                solara.HTML(tag="div", style="width:12px; height:12px; background-color:green; border-radius:50%; margin-top:4px")
                solara.Text("Purchased", style="font-size: 0.9em")
            with solara.Row(gap="5px"):
                solara.HTML(tag="div", style="width:12px; height:12px; background-color:yellow; border-radius:50%; margin-top:4px")
                solara.Text("Interested", style="font-size: 0.9em")
            with solara.Row(gap="5px"):
                solara.HTML(tag="div", style="width:12px; height:12px; background-color:cyan; border-radius:50%; margin-top:4px")
                solara.Text("Aware", style="font-size: 0.9em")
            with solara.Row(gap="5px"):
                solara.HTML(tag="div", style="width:12px; height:12px; background-color:gray; border-radius:50%; margin-top:4px")
                solara.Text("Unaware", style="font-size: 0.9em")

@solara.component
def DeepLearningView():
    is_dark = solara.lab.use_dark_effective()
    model = model_instance.value
    step = current_step.value
    
    def make_dl_fig():
        if model is None: return go.Figure()
        
        # Latest data
        df = model.datacollector.get_model_vars_dataframe()
        if df.empty: return go.Figure()
        latest = df.iloc[-1]
        total_pop = max(1, model.num_agents)
        
        # --- 5-4-3 Architecture: Matches actual ABM pipeline ---
        # Layer 0 (x=0): Input  — 5 environment signals
        # Layer 1 (x=1): Hidden — 4 cognitive stages  
        # Layer 2 (x=2): Output — 3 economic outcomes
        
        nodes = {
            # Input Layer (x=0) — Environment signals agents consume
            "Views":           [0, 4],
            "Sentiment":       [0, 3],
            "Shares":          [0, 2],
            "Conv. Rate":      [0, 1],
            "Shop Index":      [0, 0],
            # Hidden Layer (x=1) — Agent cognitive pipeline
            "Awareness":       [1, 3.5],
            "Interest":        [1, 2.5],
            "Deliberation":    [1, 1.5],
            "Purchase Prob":   [1, 0.5],
            # Output Layer (x=2) — Economic outcomes
            "Purchases":       [2, 3],
            "Revenue (GMV)":   [2, 2],
            "Net Commission":  [2, 1],
        }
        
        # --- Dynamic node sizing based on live simulation data ---
        max_views = df['Global Views'].max() if df['Global Views'].max() > 0 else 1
        
        node_config = {
            "Views":         {"size": min(55, 12 + (latest['Global Views'] / max_views * 40)),  "color": "#00BCD4"},
            "Sentiment":     {"size": 12 + (abs(latest['Sentiment Score']) * 35),                "color": "#FFC107"},
            "Shares":        {"size": min(50, 12 + (latest['Shares'] / max(1, df['Shares'].max()) * 35)), "color": "#E91E63"},
            "Conv. Rate":    {"size": 18,                                                        "color": "#9C27B0"},
            "Shop Index":    {"size": 18,                                                        "color": "#FF5722"},
            "Awareness":     {"size": 12 + (latest['Total Aware'] / total_pop * 50),             "color": "#00BCD4"},
            "Interest":      {"size": 12 + (latest['Total Interested'] / total_pop * 50),        "color": "#FF9800"},
            "Deliberation":  {"size": 20 + (latest['Total Interested'] / total_pop * 25),        "color": "#7C4DFF"},
            "Purchase Prob": {"size": 15 + (latest['Total Purchased'] / total_pop * 40),         "color": "#FF6D00"},
            "Purchases":     {"size": 12 + (latest['Total Purchased'] / total_pop * 55),         "color": "#4CAF50"},
            "Revenue (GMV)": {"size": 15 + (min(1, latest.get('Shop GMV', 0) / max(1, shop_price.value * total_pop)) * 45), "color": "#CDDC39"},
            "Net Commission":{"size": 15 + (min(1, latest.get('Net Commission', 0) / max(1, shop_price.value * total_pop * 0.1)) * 40), "color": "#8BC34A"},
        }
        
        node_x, node_y, node_text, node_sizes, node_colors = [], [], [], [], []
        for name, pos in nodes.items():
            node_x.append(pos[0])
            node_y.append(pos[1])
            cfg = node_config[name]
            node_sizes.append(cfg["size"])
            node_colors.append(cfg["color"])
            
            # Rich hover text with live values
            if name == "Views":
                node_text.append(f"Views<br>{int(latest['Global Views']):,}")
            elif name == "Sentiment":
                node_text.append(f"Sentiment<br>{latest['Sentiment Score']:.2f}")
            elif name == "Shares":
                node_text.append(f"Shares<br>{int(latest['Shares']):,}")
            elif name == "Awareness":
                node_text.append(f"Aware<br>{int(latest['Total Aware'])}/{total_pop}")
            elif name == "Interest":
                node_text.append(f"Interest<br>{int(latest['Total Interested'])}/{total_pop}")
            elif name == "Deliberation":
                node_text.append(f"Deliberation<br>(2-tick memory)")
            elif name == "Purchase Prob":
                node_text.append(f"Purch. Prob<br>(threshold)")
            elif name == "Purchases":
                node_text.append(f"Purchased<br>{int(latest['Total Purchased'])}")
            elif name == "Revenue (GMV)":
                node_text.append(f"GMV<br>฿{latest.get('Shop GMV', 0):,.0f}")
            elif name == "Net Commission":
                node_text.append(f"Commission<br>฿{latest.get('Net Commission', 0):,.0f}")
            else:
                node_text.append(name)
        
        # --- Edges with activation-based opacity ---
        edge_traces = []
        node_names = list(nodes.keys())
        
        # Activation strength (0-1) for edge brightness
        aware_pct = latest['Total Aware'] / total_pop
        interest_pct = latest['Total Interested'] / total_pop
        purch_pct = latest['Total Purchased'] / total_pop
        
        def add_edge(from_name, to_name, strength=0.3):
            i = node_names.index(from_name)
            j = node_names.index(to_name)
            opacity = max(0.08, min(0.9, strength))
            width = max(0.5, min(4, strength * 5))
            edge_traces.append(go.Scatter(
                x=[node_x[i], node_x[j]], y=[node_y[i], node_y[j]],
                mode='lines', hoverinfo='none',
                line=dict(width=width, color=f'rgba(150,200,255,{opacity})')
            ))
        
        # Input → Hidden connections (all 5 inputs feed all 4 hidden)
        for inp in ["Views", "Sentiment", "Shares", "Conv. Rate", "Shop Index"]:
            add_edge(inp, "Awareness",     strength=aware_pct * 0.8 + 0.1)
            add_edge(inp, "Interest",      strength=interest_pct * 0.8 + 0.1)
            add_edge(inp, "Deliberation",  strength=interest_pct * 0.6 + 0.05)
            add_edge(inp, "Purchase Prob", strength=purch_pct * 0.8 + 0.05)
        
        # Hidden → Output connections
        for hid in ["Awareness", "Interest", "Deliberation", "Purchase Prob"]:
            add_edge(hid, "Purchases",      strength=purch_pct * 0.9 + 0.1)
            add_edge(hid, "Revenue (GMV)",   strength=purch_pct * 0.7 + 0.05)
            add_edge(hid, "Net Commission",  strength=purch_pct * 0.5 + 0.05)
        
        # Node trace
        node_trace = go.Scatter(
            x=node_x, y=node_y, mode='markers+text',
            text=node_text, textposition="top center",
            textfont=dict(size=10),
            marker=dict(
                color=node_colors, size=node_sizes,
                line_width=2,
                line_color='white' if is_dark else '#333'
            ),
            hoverinfo='text'
        )

        fig = go.Figure(data=edge_traces + [node_trace])
        
        # Layer label annotations
        layer_labels = [
            dict(x=0, y=4.7, text="<b>INPUT LAYER</b><br>(Environment)", showarrow=False, font=dict(size=11, color="#00BCD4")),
            dict(x=1, y=4.7, text="<b>HIDDEN LAYER</b><br>(Agent Cognition)", showarrow=False, font=dict(size=11, color="#FF9800")),
            dict(x=2, y=4.7, text="<b>OUTPUT LAYER</b><br>(Economics)", showarrow=False, font=dict(size=11, color="#4CAF50")),
        ]
        
        fig.update_layout(
            title="TikTok-Net: ABM → Deep Learning Pipeline (5-4-3)",
            showlegend=False,
            annotations=layer_labels,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.5, 2.5]),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-0.8, 5.2]),
            template="plotly_dark" if is_dark else "plotly_white",
            margin=dict(b=20, l=20, r=20, t=50),
            height=500
        )
        return fig

    fig = solara.use_memo(make_dl_fig, dependencies=[step, is_dark])
    
    with solara.Card("System Architecture (Neural Mapping)"):
        solara.Markdown(
            "This view maps the ABM logic to a **Deep Learning Pipeline (5-4-3)**. "
            "Five environment signals feed four cognitive stages inside each agent, "
            "producing three economic outcomes. Node sizes pulse with live simulation data."
        )
        solara.FigurePlotly(fig)
        with solara.Columns([1, 1, 1]):
            solara.Info("INPUT (5): Views, Sentiment, Shares, CR, Shop Index")
            solara.Info("HIDDEN (4): Awareness, Interest, Deliberation, Purch. Prob")
            solara.Info("OUTPUT (3): Purchases, Revenue, Commission")

@solara.component
def CorrelationAnalysis(df):
    is_dark = solara.lab.use_dark_effective()
    # Need at least 5 points for a meaningful correlation to avoid math warnings
    if df.empty or len(df) < 5: 
        return solara.Text("Analyzing data patterns (Min 5 days required)...")
    
    # Selecting key metrics for analysis
    cols = ["Sentiment Score", "Global Views", "Total Purchased", "Net Commission"]
    valid_cols = [c for c in cols if c in df.columns]
    
    # Ensure columns have variance and at least 2 points for std calculation
    df_filtered = df[valid_cols].dropna()
    if len(df_filtered) < 2:
        return solara.Text("Waiting for more data samples...")
        
    # Filter out zero-variance columns (e.g. Total Purchased=0 early on)
    # so the correlation matrix only contains meaningful relationships
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        stds = df_filtered.std()
    cols_with_variance = [c for c in df_filtered.columns if stds.get(c, 0) > 0]
    if len(cols_with_variance) < 2:
        return solara.Text("Waiting for trend variance...")
    
    df_corr = df_filtered[cols_with_variance]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        corr_matrix = df_corr.corr()
    
    plt_template = "plotly_dark" if is_dark else "plotly_white"
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='Viridis',
        zmin=-1, zmax=1,
        text=corr_matrix.values.round(2),
        texttemplate="%{text}",
    ))
    fig.update_layout(title="Metric Correlation Matrix (Inferential)", template=plt_template, height=350)
    
    with solara.Card("Statistical Analysis"):
        solara.FigurePlotly(fig)
        solara.Markdown("*Insights: High correlation (close to 1.0) indicates that views/sentiment are strong drivers of purchases.*")

@solara.component
def AnalyticsPanel():
    is_dark = solara.lab.use_dark_effective()
    step = current_step.value
    model = model_instance.value
    product_name = trend_category.value
    plt_template = "plotly_dark" if is_dark else "plotly_white"
    
    def get_df():
        if model is None: return pd.DataFrame()
        return model.datacollector.get_model_vars_dataframe()
    
    df = solara.use_memo(get_df, dependencies=[step, model])

    def make_funnel_fig():
        if df.empty: return go.Figure()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Total Aware'], name='Aware', line=dict(color='cyan', width=2)))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Total Interested'], name='Interested', line=dict(color='orange', width=2)))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Total Purchased'], name='Purchased', line=dict(color='green', width=4)))
        fig.update_layout(title=f'Conversion Funnel: {product_name}', template=plt_template, xaxis_title="Timeline", yaxis_title="Agents")
        return fig

    def make_engagement_fig():
        if df.empty: return go.Figure()
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Global Views'], name='Views', fill='tozeroy', line=dict(color='#8A2BE2')))
        fig.add_trace(go.Scatter(x=df['Date'], y=df['Shares'], name='Shares', line=dict(color='#FF1493')))
        fig.update_layout(title='Viral Engagement Velocity', template=plt_template, xaxis_title="Timeline", yaxis_title="Count")
        return fig

    def make_revenue_fig():
        if df.empty: return go.Figure()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df['Date'], y=df['Shop GMV'], name='Gross Revenue (THB)', marker_color='gold'))
        fig.add_trace(go.Bar(x=df['Date'], y=df['Net Commission'], name='Net Commission (THB)', marker_color='limegreen'))
        fig.update_layout(title='TikTok Shop: Revenue Projection', barmode='overlay', template=plt_template, xaxis_title="Timeline", yaxis_title="Baht (฿)")
        return fig

    fig_funnel = solara.use_memo(make_funnel_fig, dependencies=[df, plt_template, product_name])
    fig_engagement = solara.use_memo(make_engagement_fig, dependencies=[df, plt_template])
    fig_revenue = solara.use_memo(make_revenue_fig, dependencies=[df, plt_template])
    
    if model is None:
        return solara.Text("No data available")

    with solara.Column():
        with solara.Card("Market Adoption Funnel"):
            solara.FigurePlotly(fig_funnel)
        with solara.Card("Trend Engagement Velocity"):
            solara.FigurePlotly(fig_engagement)

    # 3. TikTok Shop Revenue Analysis
    if use_tiktok_shop.value:
        with solara.Card("Financial Projections & GMV", margin="10px 0"):
            solara.FigurePlotly(fig_revenue)

    # 4. Advanced Data Analytics (Rubric Step 5 & 6)
    solara.Markdown("### 🧠 Advanced Predictive & Inferential Analytics", style="margin-top: 30px")
    with solara.Column():
        CorrelationAnalysis(df)
        
        with solara.Card("Predictive Model Evaluation", margin="10px 0"):
                if len(df) > 10:
                    # Use diff-based velocity (not pct_change, which breaks on 0→N)
                    purchases = df['Total Purchased']
                    window = min(5, len(purchases) - 1)
                    rate = (purchases.iloc[-1] - purchases.iloc[-(window+1)]) / max(1, window)
                    remaining = model.num_agents - purchases.iloc[-1]
                    saturation_pct = purchases.iloc[-1] / max(1, model.num_agents) * 100
                    
                    if rate > 0 and remaining > 0:
                        # ETA capped at model's max ticks (60 days)
                        max_ticks = getattr(model.env, 'max_ticks', 60)
                        raw_eta = step + int(remaining / rate)
                        eta = min(raw_eta, max_ticks + 30)  # Allow slight overshoot
                        
                        solara.Markdown(f"### 🔮 **Forecast: Market Saturation by Day {eta}**")
                        solara.Text(f"Current Velocity: {rate:.1f} conversions/day")
                        
                        # Reliability via coefficient of variation on diffs (not pct_change)
                        reliability = 0.0
                        recent = purchases.iloc[-min(15, len(purchases)):]
                        diffs = recent.diff().dropna()
                        positive_diffs = diffs[diffs > 0]
                        
                        if len(positive_diffs) >= 3:
                            mean_diff = positive_diffs.mean()
                            std_diff = positive_diffs.std()
                            if mean_diff > 0:
                                cv = std_diff / mean_diff  # Coefficient of variation
                                # CV=0 → perfect consistency (100%), CV>1 → erratic (0%)
                                reliability = max(0, min(100, 100 * (1 - min(1, cv))))
                        elif saturation_pct > 90:
                            reliability = 95.0  # Near-saturation is inherently reliable
                        
                        with solara.Column(margin="20px 0"):
                            solara.Text(f"Market Saturation: {saturation_pct:.1f}%")
                            solara.ProgressLinear(value=saturation_pct)
                            solara.Text(f"Model Reliability (CV): {reliability:.1f}%")
                            solara.ProgressLinear(value=reliability)
                            if reliability > 70:
                                solara.Markdown("*High confidence — stable conversion velocity.*")
                            elif reliability > 30:
                                solara.Markdown("*Moderate confidence — trend is still developing.*")
                            else:
                                solara.Markdown("*Low confidence — early stage, waiting for momentum.*")
                        
                        # R² Goodness-of-Fit: compare actual vs logistic curve
                        try:
                            import numpy as np
                            y_actual = purchases.values.astype(float)
                            n = len(y_actual)
                            if n >= 10 and y_actual.max() > 0:
                                # Fit a logistic growth curve: L / (1 + exp(-k*(x-x0)))
                                L = float(model.num_agents)
                                x = np.arange(n, dtype=float)
                                # Find midpoint (tick where purchases reach 50% of max)
                                half_max = y_actual.max() / 2.0
                                mid_idx = np.argmin(np.abs(y_actual - half_max))
                                x0 = float(mid_idx)
                                # Estimate growth rate from steepest slope
                                diffs_arr = np.diff(y_actual)
                                k = max(0.1, float(np.max(diffs_arr)) / (L / 4.0)) if L > 0 else 0.1
                                
                                y_pred = L / (1.0 + np.exp(-k * (x - x0)))
                                
                                ss_res = np.sum((y_actual - y_pred) ** 2)
                                ss_tot = np.sum((y_actual - np.mean(y_actual)) ** 2)
                                r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
                                r_squared = max(0.0, min(1.0, r_squared))
                                
                                with solara.Column(margin="10px 0"):
                                    solara.Markdown(f"**R² (Logistic Fit): {r_squared:.4f}**")
                                    solara.ProgressLinear(value=r_squared * 100)
                                    if r_squared > 0.90:
                                        solara.Markdown("*Excellent fit — adoption follows classic S-curve.*")
                                    elif r_squared > 0.70:
                                        solara.Markdown("*Good fit — adoption mostly follows S-curve with some noise.*")
                                    else:
                                        solara.Markdown("*Moderate fit — adoption pattern deviates from ideal S-curve.*")
                        except Exception:
                            pass  # Don't break UI if R² calc fails
                            
                    elif remaining <= 0:
                        solara.Markdown("### ✅ **Target Met: 100% Market Saturation**")
                        solara.ProgressLinear(value=100)
                    else:
                        solara.Text("Analyzing purchase velocity — no conversions yet...")
                        solara.ProgressLinear(value=max(5, saturation_pct if 'saturation_pct' in dir() else 5))
                else:
                    with solara.Column(align="center", margin="40px"):
                        solara.ProgressLinear(value=10)
                        solara.Text("Collecting data for predictive engine (need 10+ ticks)...")

    solara.Markdown("---")

@solara.component
def LiveStatsPanel():
    step = current_step.value # This dependency ensures real-time updates
    model = model_instance.value
    if model is None: return
    
    df = model.datacollector.get_model_vars_dataframe()
    if len(df) == 0:
        last = {"Sentiment Score": 0.0, "Total Aware": 0, "Total Purchased": 0, "Shop GMV": 0, "Date": "Initializing..."}
    else:
        last = df.iloc[-1]
    
    current_date = last.get("Date", "---")
        
    with solara.Columns([1, 1, 1, 1]):
        with solara.Card("Live Sentiment", subtitle=f"Date: {current_date}"):
            val = last.get('Sentiment Score', 0.0)
            color = "green" if val > 0.7 else "orange" if val > 0.4 else "red"
            solara.Text(f"{val:.2f}", style=f"font-size: 2em; font-weight: bold; color: {color}")
            
        with solara.Card("Market Aware", subtitle="Brand Recognition"):
            val = int(last.get('Total Aware', 0))
            solara.Text(f"{val}", style="font-size: 2em; font-weight: bold; color: cyan")
            
        with solara.Card("Conversions", subtitle="Units Sold"):
            val = int(last.get('Total Purchased', 0))
            solara.Text(f"{val}", style="font-size: 2em; font-weight: bold; color: #4CAF50")
            
        with solara.Card("Projected GMV", subtitle="Total Revenue"):
            val = last.get('Shop GMV', 0) if use_tiktok_shop.value else 0
            solara.Text(f"฿{val:,.0f}", style="font-size: 2em; font-weight: bold; color: gold")

@solara.component
def UI():
    solara.use_thread(run_simulation_loop, dependencies=[])
    solara.use_effect(init_model, [trend_category.value, n_agents.value, sentiment_multiplier.value, influence_radius.value, market_volatility.value, use_tiktok_shop.value, shop_price.value, shop_commission.value])
    
    model = model_instance.value
    if model is None: return
    
    with solara.Column():
        with solara.Row(justify="end", margin="10px", gap="8px"):
            solara.Button(
                "Wiki Proxy",
                on_click=refresh_data,
                disabled=is_fetching.value,
                icon_name="public",
                color="warning",
                outlined=True,
            )
            solara.Button(
                "TikTok Scrape",
                on_click=deep_scrape_data,
                color="success",
                disabled=is_fetching.value,
                icon_name="cloud_download",
            )
            solara.lab.ThemeToggle()
            
        LiveStatsPanel()

    with solara.Columns([1, 3]):
        with solara.Column():
            with solara.Card("Calibration"):
                solara.Select("Trend Context", values=TREND_CATEGORIES, value=trend_category)
                solara.SliderInt("Agents", value=n_agents, min=50, max=500)
                solara.SliderFloat("Impact", value=sentiment_multiplier, min=0.1, max=3.0)
                solara.SliderInt("Reach", value=influence_radius, min=1, max=4)
                solara.SliderFloat("Tick Interval (s)", value=simulation_speed, min=0.1, max=2.0)
            with solara.Card("TikTok Shop"):
                solara.Checkbox(label="Enable Shop Impulse", value=use_tiktok_shop)
                if use_tiktok_shop.value:
                    solara.SliderInt("Price (THB)", value=shop_price, min=99, max=5000)
                    solara.SliderFloat("Comm %", value=shop_commission, min=1, max=30)

        with solara.Column():
            with solara.lab.Tabs():
                with solara.lab.Tab("Analytics Dashboard"):
                    AnalyticsPanel()
                with solara.lab.Tab("Social Network Graph"):
                    with solara.Card("Global Network Awareness"):
                        AgentNetworkView()
                        with solara.Row(justify="center"):
                            solara.Button("Reset", on_click=init_model, outlined=True)
                            if simulation_running.value:
                                solara.Button("Pause", on_click=lambda: simulation_running.set(False), color="warning")
                            else:
                                solara.Button("Play", on_click=lambda: simulation_running.set(True), color="success")
                with solara.lab.Tab("System Architecture (DL Mapping)"):
                    DeepLearningView()

page = UI
