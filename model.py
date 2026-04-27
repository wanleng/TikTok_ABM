import mesa
import networkx as nx
from agents import Innovator, Follower, Skeptic
from environment import DataEnvironment

# Function to extract data for DataCollector
# Helper functions for DataCollector
def get_total_aware(model):
    return sum([1 for a in model.agents if a.is_aware])

def get_total_interested(model):
    return sum([1 for a in model.agents if a.is_interested])

def get_total_purchased(model):
    return sum([1 for a in model.agents if a.purchased])

class TikTokModel(mesa.Model):
    """
    ABM simulating TikTok trend diffusion across a social network.
    """
    def __init__(self, n_agents=500, prob_innovator=0.1, prob_follower=0.7, prob_skeptic=0.2, avg_node_degree=4, sentiment_multiplier=1.0, influence_radius=1, randomness=0.0, trend_category="Outdoor (Water Guns)", use_tiktok_shop=True, shop_price=299, shop_commission=10):
        super().__init__()
        self.num_agents = n_agents
        self.sentiment_multiplier = sentiment_multiplier
        self.influence_radius = influence_radius
        self.randomness = randomness
        self.trend_category = trend_category
        self.use_tiktok_shop = use_tiktok_shop
        self.shop_price = shop_price
        self.shop_commission = shop_commission
        
        # We use a watts_strogatz_graph for realistic social network properties (small-world)
        self.G = nx.watts_strogatz_graph(n=self.num_agents, k=avg_node_degree, p=0.1)
        
        # NetworkGrid places agents on the networkx graph
        self.grid = mesa.space.NetworkGrid(self.G)
        
        self.env = DataEnvironment()
        
        # Create Agents
        for i, node in enumerate(self.G.nodes()):
            # Decide agent type
            r = self.random.random()
            if r < prob_innovator:
                a = Innovator(self)
            elif r < prob_innovator + prob_follower:
                a = Follower(self)
            else:
                a = Skeptic(self)
            
            self.grid.place_agent(a, node)
            
        # DataCollector hooks to gather statistics over time
        self.datacollector = mesa.DataCollector(
            model_reporters={
                "Date": lambda m: m.env.get_current_date(),
                "Total Aware": get_total_aware,
                "Total Interested": get_total_interested,
                "Total Purchased": get_total_purchased,
                "Sentiment Score": lambda m: m.env.get_sentiment_score(),
                "Global Views": lambda m: m.env.get_global_views(),
                "Shares": lambda m: m.env.get_shares(),
                "Shop GMV": lambda m: get_total_purchased(m) * m.shop_price,
                "Net Commission": lambda m: (get_total_purchased(m) * m.shop_price) * (m.shop_commission / 100.0)
            },
            agent_reporters={
                "agent_type": "agent_type",
                "is_aware": "is_aware",
                "is_interested": "is_interested",
                "purchased": "purchased",
                "purchase_tick": "purchase_tick"
            }
        )

    def step(self):
        """
        Advance the model by one step.
        """
        self.datacollector.collect(self)
        self.env.step()
        self.agents.shuffle_do("step")
