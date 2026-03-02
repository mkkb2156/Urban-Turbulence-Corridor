# UTC 演算法與學術參考

## Phase 1 核心方法

### FAI (Frontal Area Index)

```
FAI(θ) = Σ(建物垂直於 θ 方向的投影面積) / 網格地面面積
```

- 每個 100m 網格計算 16 個方向（每 22.5°）
- 處理跨網格建物：以 `gpd.overlay(intersection)` 裁切

### LCP (Least Cost Path)

1. FAI → 阻力面（低 FAI = 低阻力）
2. 風源點設定（關渡隘口、基隆河谷、新店溪谷口）
3. Dijkstra 最短路徑（8 連通鄰域）
4. 回溯最低成本路徑 = 風廊

### 對數風速剖面

```
U(z) = (u* / κ) × ln((z - zd) / z₀)
```

粗糙度參數由 MacDonald et al. (1998) 形態學方法計算。

## 關鍵參考文獻

1. Hsieh & Huang (2016) — 台南 LCP 風廊研究
2. Wong et al. (2010) — 香港 UCMap
3. Ng et al. (2011) — 香港 AVA 技術指引
4. MacDonald et al. (1998) — 都市粗糙度形態學方法
