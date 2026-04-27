import solara
from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from model import TikTokModel
from agents import Innovator, Follower, Skeptic

# 1. Provide an agent portrayal function
def agent_portrayal(agent):
    """
    Determines how agents are visually styled on the network graph based on their class and states.
    """
    # Default unpurchased state
    color = "tab:gray"
    size = 10
    
    # If the agent has purchased, apply their class-specific color
    if agent.purchased:
        size = 15
        if isinstance(agent, Innovator):
            color = "tab:blue" # Blue for Innovators
        elif isinstance(agent, Follower):
            color = "tab:orange" # Orange for Followers
        elif isinstance(agent, Skeptic):
            color = "tab:red" # Red for Skeptics

    return {
        "color": color,
        "size": size,
    }

# 2. Define user-configurable parameters via Sliders
model_params = {
    "n_agents": {
        "type": "SliderInt",
        "value": 200,
        "label": "Number of Agents",
        "min": 10,
        "max": 1000,
        "step": 10,
    },
    "prob_innovator": {
        "type": "SliderFloat",
        "value": 0.1,
        "label": "Probability of Innovators",
        "min": 0.0,
        "max": 1.0,
        "step": 0.05,
    },
    "prob_follower": {
        "type": "SliderFloat",
        "value": 0.7,
        "label": "Probability of Followers",
        "min": 0.0,
        "max": 1.0,
        "step": 0.05,
    },
    "prob_skeptic": {
        "type": "SliderFloat",
        "value": 0.2,
        "label": "Probability of Skeptics",
        "min": 0.0,
        "max": 1.0,
        "step": 0.05,
    },
}

# 3. Create visual components
space_component = make_space_component(agent_portrayal)
plot_component = make_plot_component({
    "Total Purchased": "tab:blue",
    "Sentiment Score": "tab:orange"
})

# 4. Instantiate the app logic
model1 = TikTokModel()

page = SolaraViz(
    model1,
    components=[space_component, plot_component],
    model_params=model_params,
    name="TikTok Trend ABM"
)

# This command structure exposes the Solara app instance
# when running `solara run app.py`
