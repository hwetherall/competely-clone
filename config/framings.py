"""
Competitor discovery framing definitions and Innovera-tuned defaults.
"""

from typing import Literal

DiscoveryFraming = Literal["direct", "problem_sharer", "category_sharer", "adjacency"]

FRAMING_LABELS: dict[str, str] = {
    "direct": "Direct",
    "problem_sharer": "Problem-Sharer",
    "category_sharer": "Category-Sharer",
    "adjacency": "Adjacency",
}

FRAMING_DEFINITIONS: dict[str, str] = {
    "direct": "Same problem, same solution shape.",
    "problem_sharer": "Same problem, different solution.",
    "category_sharer": "Different problem, same solution shape.",
    "adjacency": "Capital, technology, data, or distribution to pivot into the target's space.",
}

DEFAULT_FRAMING_SEEDS: dict[str, str] = {
    "direct": (
        "Other AI-native decision intelligence, strategy, market research, competitive analysis, "
        "or initiative digital-twin platforms."
    ),
    "problem_sharer": (
        "Consulting firms and expert networks solving strategic decisions under uncertainty, "
        "including blended AI plus human models such as McKinsey QuantumBlack, BCG X, Bain Vector, "
        "Accenture, GLG, and Third Bridge."
    ),
    "category_sharer": (
        "Multi-agent AI research, enterprise knowledge, analyst, and market-intelligence platforms "
        "with adjacent solution shapes, such as Glean, Hebbia, Rogo, AlphaSense, and AI analyst tools."
    ),
    "adjacency": (
        "Big 4 firms, foundation-model labs, CRMs/ERPs, Palantir-like decision layers, sovereign funds, "
        "and trading houses with data, capital, or distribution that could enter decision intelligence."
    ),
}

FRAMING_WEIGHTS: dict[str, float] = {
    "direct": 1.25,
    "problem_sharer": 1.05,
    "category_sharer": 0.95,
    "adjacency": 0.75,
}

DISCOVERY_FRAMINGS: tuple[str, ...] = (
    "direct",
    "problem_sharer",
    "category_sharer",
    "adjacency",
)

