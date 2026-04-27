import mesa
import math

class ConsumerAgent(mesa.Agent):
    """
    Base class for TikTok Consumer Agents on a social network.
    Now tracking a 3-stage marketing funnel: Aware -> Interested -> Purchased.
    """
    def __init__(self, model):
        super().__init__(model)
        self.is_aware = False
        self.is_interested = False
        self.purchased = False # acts as has_purchased
        self.agent_type = "Consumer"  # Overridden by subclasses
        self.purchase_tick = -1       # -1 = never purchased
        
        self.ticks_seen_positive = 0
        self.deliberation_ticks = 0
        self.purchase_probability = 0.0
        self.influence_threshold = 1.0 # default high threshold
        self.interest_threshold = 0.5 # default interest floor
        
    def calculate_intent(self, sentiment_score, neighbor_purchases, num_neighbors):
        """
        Calculates buying intent based on global sentiment and local social proof.
        """
        # Base intent from global sentiment scaled by user multiplier
        intent = (sentiment_score * getattr(self.model, "sentiment_multiplier", 1.0)) * self.purchase_probability
        
        # Social proof from network: increase intent if neighbors have purchased
        if num_neighbors > 0:
            social_proof = neighbor_purchases / num_neighbors
            intent += social_proof * 0.5 # 50% weight on social proof
            
        return intent

    def step(self):
        """
        Agent evaluates whether to transition through the funnel.
        """
        if self.purchased:
            return

        # 1. Environment Stats
        sentiment = self.model.env.get_sentiment_score()
        views = self.model.env.get_global_views()
        shares = self.model.env.get_shares()
        conv_rate = self.model.env.get_conversion_rate()
        
        # 2. Network Stats
        inf_radius = getattr(self.model, "influence_radius", 1)
        if inf_radius == 1:
            neighbors = self.model.grid.get_neighbors(self.pos, include_center=False)
        else:
            import networkx as nx
            neighbor_nodes = list(nx.single_source_shortest_path_length(self.model.G, self.pos, cutoff=inf_radius).keys())
            if self.pos in neighbor_nodes:
                neighbor_nodes.remove(self.pos)
            neighbors = self.model.grid.get_cell_list_contents(neighbor_nodes)
            
        num_neighbors = len(neighbors)
        neighbor_purchases = sum([1 for n in neighbors if n.purchased])
        neighbor_aware = sum([1 for n in neighbors if n.is_aware])
        
        # --- FUNNEL STAGE 1: Unaware -> Aware ---
        # Influence Reach: Driven by views, shares, and neighbor awareness
        if not self.is_aware:
            # Fashion items spread faster via visual shares
            share_multiplier = 1.0
            category = getattr(self.model, "trend_category", "").lower()
            if any(k in category for k in ["shirt", "shorts", "sandal"]):
                share_multiplier = 2.0
                
            # Use environment's dynamic divisor to handle varying data scales
            divisor = self.model.env.get_view_divisor()
            reach_score = (views / divisor) + (shares / (divisor * 0.1)) * share_multiplier
            if num_neighbors > 0:
                reach_score += (neighbor_aware / num_neighbors) * 0.4 # Higher social discovery weight
            
            # Stricter awareness entry
            if reach_score > (self.influence_threshold * 0.2):
                self.is_aware = True

        # --- FUNNEL STAGE 2: Aware -> Interested ---
        # Stage 2: Interest (Requires Awareness + sustained Sentiment/Social Proof)
        if self.is_aware and not self.is_interested:
            if sentiment > self.interest_threshold:
                self.deliberation_ticks += 1
                # Require 2 consecutive qualifying ticks to simulate deliberation
                if self.deliberation_ticks >= 2:
                    self.is_interested = True
                    # If they just became interested, they STOP for this tick (no instant purchase)
                    return
            else:
                # Cold feet: reset deliberation if sentiment drops
                self.deliberation_ticks = max(0, self.deliberation_ticks - 1)

        # --- FUNNEL STAGE 3: Interested -> Purchased ---
        # Driven by Market Volatility Equation, Conversion Baseline, and TikTok Shop Impulse
        if self.is_interested and not self.purchased:
            intent = self.calculate_intent(sentiment, neighbor_purchases, num_neighbors)
            
            # Use real-world conversion rates and shop signals
            shop_index = self.model.env.get_shop_index()
            current_tick = self.model.env.current_tick
            
            # Impulse Factor: exponential decay simulating buying fatigue
            # Decay tuned for 60-day window (2.5x early -> ~0.8x late)
            impulse_factor = 2.5 * math.exp(-0.02 * current_tick)
            
            # Base probability derived from intent + real data signals
            base_prob = (conv_rate * 2.0) + (intent * 0.5)
            
            # Apply impulse decay and shop boost (up to 300% based on real Shop Index)
            shop_boost = (shop_index * 3.0)
            base_prob *= impulse_factor * (1 + shop_boost)
            
            # Market Volatility (σ): stochastic noise component
            # σ=0 is fully deterministic, σ=1 is fully random
            sigma = self.model.randomness
            epsilon = self.random.random()
            final_prob = base_prob * (1 - sigma) + (sigma * epsilon)
                
            if final_prob >= self.influence_threshold:
                self.purchased = True
                self.purchase_tick = current_tick


class Innovator(ConsumerAgent):
    """
    Early adopters; low threshold for awareness and high base conversion.
    """
    def __init__(self, model):
        super().__init__(model)
        self.agent_type = "Innovator"
        self.purchase_probability = 0.9 # Increased from 0.8
        self.influence_threshold = 0.3 # Lowered from 0.4
        self.interest_threshold = 0.2
        
        # Beauty Logic Buff
        category = getattr(self.model, "trend_category", "").lower()
        if any(k in category for k in ["sunscreen", "makeup", "mist"]):
            self.purchase_probability += 0.15
            self.influence_threshold -= 0.1


class Follower(ConsumerAgent):
    """
    Doubtful without social proof; scales intent with views and neighbor behavior.
    """
    def __init__(self, model):
        super().__init__(model)
        self.agent_type = "Follower"
        self.purchase_probability = 0.6 # Increased from 0.5
        self.influence_threshold = 0.5 # Lowered from 0.7
        self.interest_threshold = 0.4
        
    def calculate_intent(self, sentiment_score, neighbor_purchases, num_neighbors):
        base_intent = super().calculate_intent(sentiment_score, neighbor_purchases, num_neighbors)
        
        views = self.model.env.get_global_views()
        divisor = self.model.env.get_view_divisor()
        # View factor now scales with the trend potential
        view_factor = min(0.4, (views / divisor) * 0.4)
        
        # Songkran Category Logic Buff
        category = getattr(self.model, "trend_category", "").lower()
        if any(k in category for k in ["gun", "bucket", "ticket"]):
            base_intent += 0.25 # β_trend: Outdoor category seasonal demand boost (Section 4)
            
        return base_intent + view_factor


class Skeptic(ConsumerAgent):
    """
    Resistant; requires multiple positive signals and high local adoption.
    """
    def __init__(self, model):
        super().__init__(model)
        self.agent_type = "Skeptic"
        self.purchase_probability = 0.3 # Increased from 0.2
        self.influence_threshold = 0.8 # Lowered from 0.9
        self.interest_threshold = 0.7
        
    def step(self):
        # Skeptics have unique 'patience' logic before entering the funnel
        if self.purchased:
            return
            
        sentiment = self.model.env.get_sentiment_score()
        if sentiment > 0.65:
            self.ticks_seen_positive += 1
        elif sentiment < 0.5:
            # Only reset on genuinely negative signals, not mild dips
            self.ticks_seen_positive = max(0, self.ticks_seen_positive - 1)
        # If 0.5 <= sentiment <= 0.65: counter holds steady (neutral zone)
            
        # Only enter the Aware/Interested stages if they've seen prolonged hype
        # Tech items have higher curiosity, reducing wait time for skeptics
        # Increased wait threshold for 60-day trend realism
        wait_threshold = 4 # Increased from 2 for better lag effect
        category = getattr(self.model, "trend_category", "").lower()
        if any(k in category for k in ["case", "camera", "speaker"]):
            wait_threshold = 2
            
        if self.ticks_seen_positive >= wait_threshold or self.is_aware:
            super().step()
