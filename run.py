from model import TikTokModel
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

def run_simulation(steps=60, num_agents=500, shop_enabled=True, shop_price=299.0, shop_commission=10.0, label="default"):
    """Run a single simulation and return model + dataframes."""
    print(f"  [{label}] Running {num_agents} agents, {steps} steps, Shop={'ON' if shop_enabled else 'OFF'}...")
    
    model = TikTokModel(
        n_agents=num_agents,
        prob_innovator=0.1,
        prob_follower=0.7,
        prob_skeptic=0.2,
        avg_node_degree=6,
        use_tiktok_shop=shop_enabled,
        shop_price=shop_price,
        shop_commission=shop_commission
    )
    
    for i in range(steps):
        model.step()
    
    # Extract data
    model_df = model.datacollector.get_model_vars_dataframe()
    trend_category = getattr(model.env, 'active_category', 'Unknown')
    model_df["Trend_Category"] = trend_category
    
    agent_df = model.datacollector.get_agent_vars_dataframe()
    
    return model, model_df, agent_df


def export_results(model_df, agent_df, model, output_dir="output"):
    """Export simulation results, agent-level analysis, and visualizations."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # 1. Model-level CSV
    csv_path = os.path.join(output_dir, "simulation_results.csv")
    model_df.to_csv(csv_path, index_label="Tick")
    print(f"Metrics exported to {csv_path}")
    
    # 2. Agent-level analysis
    export_agent_analysis(agent_df, model, output_dir)
    
    # 3. Trend diffusion plot
    export_trend_plot(model_df, output_dir)
    
    # 4. Show stats
    print("\nDescriptive Statistics (Purchases over Time):")
    print(model_df["Total Purchased"].describe())


def export_agent_analysis(agent_df, model, output_dir="output"):
    """Export per-agent-type purchase timing analysis."""
    # Get final tick's agent data
    last_step = agent_df.index.get_level_values(0).max()
    final_agents = agent_df.xs(last_step, level="Step")
    
    # Summary by agent type
    type_summary = final_agents.groupby("agent_type").agg(
        total_agents=("purchased", "count"),
        total_purchased=("purchased", "sum"),
        avg_purchase_tick=("purchase_tick", lambda x: x[x >= 0].mean() if (x >= 0).any() else -1),
        earliest_purchase=("purchase_tick", lambda x: x[x >= 0].min() if (x >= 0).any() else -1),
        latest_purchase=("purchase_tick", lambda x: x[x >= 0].max() if (x >= 0).any() else -1)
    ).reset_index()
    
    type_summary["conversion_rate"] = (type_summary["total_purchased"] / type_summary["total_agents"] * 100).round(1)
    type_summary["avg_purchase_tick"] = type_summary["avg_purchase_tick"].round(1)
    
    agent_csv = os.path.join(output_dir, "agent_type_analysis.csv")
    type_summary.to_csv(agent_csv, index=False)
    print(f"Agent-type analysis exported to {agent_csv}")
    
    print("\nAgent-Type Purchase Timing:")
    print(type_summary.to_string(index=False))
    

def export_trend_plot(model_df, output_dir="output"):
    """Generate the dual-axis trend diffusion chart."""
    fig, ax1 = plt.subplots(figsize=(10, 6))

    color = 'tab:blue'
    ax1.set_xlabel('Time (Ticks)')
    ax1.set_ylabel('Total Purchased', color=color)
    ax1.plot(model_df.index, model_df["Total Purchased"], color=color, linewidth=2, label="Purchases")
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  
    color = 'tab:orange'
    ax2.set_ylabel('Sentiment & Relative Views', color=color)  
    ax2.plot(model_df.index, model_df["Sentiment Score"], color=color, linestyle='--', label="Sentiment")
    
    max_views = model_df["Global Views"].max() if model_df["Global Views"].max() > 0 else 1
    ax2.plot(model_df.index, model_df["Global Views"] / max_views, color='tab:green', linestyle=':', label="Scaled Views")
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()  
    plt.title("TikTok Trend Diffusion: Purchases vs Environment")
    
    lines_1, labels_1 = ax1.get_legend_handles_labels()
    lines_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left')

    plot_path = os.path.join(output_dir, "trend_diffusion.png")
    plt.savefig(plot_path, dpi=150)
    plt.close()
    print(f"Plot saved to {plot_path}")


def run_scenario_comparison(steps=60, num_agents=500):
    """
    Run multiple scenarios and produce a comparison report.
    Scenarios: Shop ON vs Shop OFF, and different agent counts.
    """
    print("=" * 60)
    print("  MULTI-SCENARIO COMPARISON")
    print("=" * 60)
    
    output_dir = "output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    scenarios = [
        {"label": "Base (500 agents, Shop ON)",  "num_agents": 500, "shop_enabled": True},
        {"label": "No Shop (500 agents, Shop OFF)", "num_agents": 500, "shop_enabled": False},
        {"label": "Small (100 agents, Shop ON)",  "num_agents": 100, "shop_enabled": True},
        {"label": "Large (1000 agents, Shop ON)", "num_agents": 1000, "shop_enabled": True},
    ]
    
    comparison_rows = []
    all_purchase_series = {}
    
    for sc in scenarios:
        model, model_df, agent_df = run_simulation(
            steps=steps,
            num_agents=sc["num_agents"],
            shop_enabled=sc["shop_enabled"],
            label=sc["label"]
        )
        
        # Get final tick's agent data for type analysis
        last_step = agent_df.index.get_level_values(0).max()
        final_agents = agent_df.xs(last_step, level="Step")
        
        max_purchased = model_df["Total Purchased"].max()
        max_gmv = model_df["Shop GMV"].max()
        
        # Find first purchase tick
        purchased_rows = model_df[model_df["Total Purchased"] > 0]
        first_purchase_tick = int(purchased_rows.index[0]) if len(purchased_rows) > 0 else -1
        
        # Conversion by type
        type_conv = final_agents.groupby("agent_type")["purchased"].mean() * 100
        
        comparison_rows.append({
            "Scenario": sc["label"],
            "Agents": sc["num_agents"],
            "TikTok Shop": "ON" if sc["shop_enabled"] else "OFF",
            "Final Purchased": int(max_purchased),
            "Penetration %": round(max_purchased / sc["num_agents"] * 100, 1),
            "First Purchase Tick": first_purchase_tick,
            "Final GMV (THB)": int(max_gmv),
            "Innovator Conv %": round(type_conv.get("Innovator", 0), 1),
            "Follower Conv %": round(type_conv.get("Follower", 0), 1),
            "Skeptic Conv %": round(type_conv.get("Skeptic", 0), 1)
        })
        
        # Normalize purchases for comparison plot
        all_purchase_series[sc["label"]] = model_df["Total Purchased"] / sc["num_agents"] * 100
    
    # Save comparison CSV
    comp_df = pd.DataFrame(comparison_rows)
    comp_csv = os.path.join(output_dir, "scenario_comparison.csv")
    comp_df.to_csv(comp_csv, index=False)
    print(f"\nComparison exported to {comp_csv}")
    print("\n" + comp_df.to_string(index=False))
    
    # Generate comparison chart
    fig, ax = plt.subplots(figsize=(12, 6))
    for label, series in all_purchase_series.items():
        ax.plot(series.values, linewidth=2, label=label)
    ax.set_xlabel("Tick (Day)")
    ax.set_ylabel("Market Penetration (%)")
    ax.set_title("Scenario Comparison: Market Penetration Over Time")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    comp_plot = os.path.join(output_dir, "scenario_comparison.png")
    plt.savefig(comp_plot, dpi=150)
    plt.close()
    print(f"Comparison chart saved to {comp_plot}")


if __name__ == "__main__":
    print("=" * 60)
    print("  STANDARD SIMULATION (60 steps, 500 agents)")
    print("=" * 60)
    
    # Run main simulation
    model, model_df, agent_df = run_simulation(steps=60, num_agents=500, label="Main")
    export_results(model_df, agent_df, model)
    
    print()
    
    # Run multi-scenario comparison
    run_scenario_comparison(steps=60, num_agents=500)
