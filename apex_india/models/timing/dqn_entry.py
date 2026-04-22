"""
APEX INDIA — DQN Entry Timing Agent
======================================
Deep Q-Network (RL) agent for learning optimal entry timing.
Falls back to a heuristic rule-based agent if PyTorch/TF unavailable.

State:  [RSI, ADX, BB%B, VWAP_position, volume_ratio, atr_ratio, hour_of_day]
Action: ENTER_NOW, WAIT, SKIP
Reward: Realized P&L from the trade

Usage:
    agent = DQNEntryAgent()
    action = agent.act(state)
    agent.learn(state, action, reward, next_state)
"""

import numpy as np
from collections import deque
import random
from typing import Any, Dict, List, Optional, Tuple

from apex_india.utils.logger import get_logger

logger = get_logger("models.timing.dqn")

# Optional deep learning import
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class DQNEntryAgent:
    """
    Deep Q-Network agent for optimal entry timing.
    Falls back to rule-based heuristic if PyTorch unavailable.
    """

    # Actions
    ENTER_NOW = 0
    WAIT = 1
    SKIP = 2
    ACTION_NAMES = {0: "ENTER_NOW", 1: "WAIT", 2: "SKIP"}

    STATE_DIM = 8
    ACTION_DIM = 3

    def __init__(
        self,
        learning_rate: float = 0.001,
        gamma: float = 0.95,
        epsilon: float = 1.0,
        epsilon_min: float = 0.05,
        epsilon_decay: float = 0.995,
        memory_size: int = 10000,
        batch_size: int = 64,
    ):
        self.lr = learning_rate
        self.gamma = gamma
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size

        self._memory = deque(maxlen=memory_size)
        self._model = None
        self._target_model = None
        self._optimizer = None
        self._step_count = 0

        if HAS_TORCH:
            self._build_network()
            logger.info("DQN agent initialized with PyTorch")
        else:
            logger.info("DQN agent using rule-based fallback (PyTorch not available)")

    def _build_network(self):
        """Build Q-network."""
        if not HAS_TORCH:
            return

        class QNetwork(nn.Module):
            def __init__(self, state_dim, action_dim):
                super().__init__()
                self.net = nn.Sequential(
                    nn.Linear(state_dim, 64),
                    nn.ReLU(),
                    nn.Linear(64, 64),
                    nn.ReLU(),
                    nn.Linear(64, 32),
                    nn.ReLU(),
                    nn.Linear(32, action_dim),
                )

            def forward(self, x):
                return self.net(x)

        self._model = QNetwork(self.STATE_DIM, self.ACTION_DIM)
        self._target_model = QNetwork(self.STATE_DIM, self.ACTION_DIM)
        self._target_model.load_state_dict(self._model.state_dict())
        self._optimizer = optim.Adam(self._model.parameters(), lr=self.lr)

    # ───────────────────────────────────────────────────────────
    # State Construction
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def build_state(
        rsi: float = 50,
        adx: float = 20,
        bb_pct_b: float = 0.5,
        vwap_position: float = 0,
        volume_ratio: float = 1.0,
        atr_ratio: float = 1.0,
        hour: float = 12.0,
        trend_strength: float = 0.0,
    ) -> np.ndarray:
        """Normalize state features to [0, 1] range."""
        return np.array([
            rsi / 100,
            min(adx / 50, 1),
            np.clip(bb_pct_b, 0, 1),
            np.clip((vwap_position + 3) / 6, 0, 1),  # -3 to +3 std devs
            min(volume_ratio / 3, 1),
            min(atr_ratio / 2, 1),
            (hour - 9) / 6.5,   # 9:00 to 15:30
            np.clip((trend_strength + 1) / 2, 0, 1),
        ], dtype=np.float32)

    # ───────────────────────────────────────────────────────────
    # Action Selection
    # ───────────────────────────────────────────────────────────

    def act(self, state: np.ndarray) -> int:
        """Select action with epsilon-greedy policy."""
        if not HAS_TORCH or self._model is None:
            return self._rule_based_action(state)

        # Epsilon-greedy
        if random.random() < self.epsilon:
            return random.randint(0, self.ACTION_DIM - 1)

        with torch.no_grad():
            state_t = torch.FloatTensor(state).unsqueeze(0)
            q_values = self._model(state_t)
            return int(q_values.argmax(1).item())

    def _rule_based_action(self, state: np.ndarray) -> int:
        """Heuristic fallback when no NN available."""
        rsi = state[0] * 100
        adx = state[1] * 50
        volume_ratio = state[4] * 3

        # Strong entry conditions
        if adx > 25 and volume_ratio > 1.2:
            if 40 < rsi < 70:
                return self.ENTER_NOW

        # Avoid extreme RSI
        if rsi > 80 or rsi < 20:
            return self.SKIP

        return self.WAIT

    # ───────────────────────────────────────────────────────────
    # Learning
    # ───────────────────────────────────────────────────────────

    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> None:
        """Store experience in replay buffer."""
        self._memory.append((state, action, reward, next_state, done))

    def learn(self) -> Optional[float]:
        """Train on a batch from replay buffer."""
        if not HAS_TORCH or self._model is None:
            return None

        if len(self._memory) < self.batch_size:
            return None

        batch = random.sample(self._memory, self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)

        states_t = torch.FloatTensor(np.array(states))
        actions_t = torch.LongTensor(actions).unsqueeze(1)
        rewards_t = torch.FloatTensor(rewards)
        next_states_t = torch.FloatTensor(np.array(next_states))
        dones_t = torch.FloatTensor(dones)

        # Current Q values
        current_q = self._model(states_t).gather(1, actions_t).squeeze()

        # Target Q values
        with torch.no_grad():
            next_q = self._target_model(next_states_t).max(1)[0]
            target_q = rewards_t + self.gamma * next_q * (1 - dones_t)

        # Loss
        loss = nn.MSELoss()(current_q, target_q)

        self._optimizer.zero_grad()
        loss.backward()
        self._optimizer.step()

        # Decay epsilon
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

        # Update target network periodically
        self._step_count += 1
        if self._step_count % 100 == 0:
            self._target_model.load_state_dict(self._model.state_dict())

        return float(loss.item())

    def get_action_name(self, action: int) -> str:
        """Get human-readable action name."""
        return self.ACTION_NAMES.get(action, "UNKNOWN")

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "has_torch": HAS_TORCH,
            "epsilon": round(self.epsilon, 4),
            "memory_size": len(self._memory),
            "steps": self._step_count,
            "mode": "DQN" if HAS_TORCH else "rule_based",
        }
