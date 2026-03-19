"""Weibull 風速分布（Phase 2）。

Weibull 分布用於描述風速的統計特性：
f(v) = (k/c) × (v/c)^(k-1) × exp(-(v/c)^k)

其中 k = 形狀參數，c = 尺度參數。
"""

from __future__ import annotations

import logging

import numpy as np
from scipy.stats import weibull_min

logger = logging.getLogger(__name__)


def fit_weibull(
    wind_speeds: np.ndarray,
) -> tuple[float, float]:
    """擬合 Weibull 分布參數。

    Args:
        wind_speeds: 風速觀測值陣列（m/s）。

    Returns:
        (k, c) — 形狀參數與尺度參數。
    """
    # 移除零值與負值
    speeds = wind_speeds[wind_speeds > 0]
    if len(speeds) < 10:
        logger.warning("Too few valid wind speed samples (%d)", len(speeds))
        return 2.0, speeds.mean() if len(speeds) > 0 else 5.0

    # scipy weibull_min 擬合
    k, _, c = weibull_min.fit(speeds, floc=0)

    logger.info("Weibull fit: k=%.2f, c=%.2f", k, c)
    return k, c


def weibull_exceedance_probability(
    threshold: float,
    k: float,
    c: float,
) -> float:
    """計算超過門檻風速的機率。

    P(v > threshold) = exp(-(threshold/c)^k)

    Args:
        threshold: 風速門檻（m/s）。
        k: Weibull 形狀參數。
        c: Weibull 尺度參數。

    Returns:
        超過門檻的機率（0-1）。
    """
    return float(np.exp(-(threshold / c) ** k))
