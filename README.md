# UTC v4 — Urban Turbulence Corridor

台灣城市風廊圖層系統 — 無人機低空作業風險評估平台

**決策工具，不是資料瀏覽器。一個問題，一個答案：「今天能飛嗎？」**

## 技術棧

- **前端**: React 19 + MapLibre GL v4 + Deck.gl v9 + WebGL GPU 風場粒子
- **後端**: FastAPI + PostGIS + 27 API endpoints
- **圖磚**: Martin (Rust) — PostGIS → MVT 向量圖磚
- **部署**: Fly.io (Martin + API) + Cloudflare Pages

## 快速開始

```bash
# 前端
cd apps/web && npm install && npm run dev

# 後端
cd services/api && pip install -r requirements.txt
uvicorn main:app --reload

# Docker 全端
cd infra && docker compose up
```

## 核心功能

- 單頁地圖 UX：點地圖 → 選機型 → 選時間 → 右側面板顯示 GO/CAUTION/NO-GO
- WebGL GPU 粒子風場動畫（100K+ 粒子 60fps）
- Martin 向量圖磚（支援 10 萬+ 網格）
- 72h 風場預報 + 最佳飛行時段
- 6 款 DJI 無人機安全閾值檢查
- 電池消耗估算 + 風廊加速警告

## 授權

MIT License
