# UTC 系統架構

## 概述

UTC 採用分層架構，從原始資料到最終 API 輸出：

```
資料取得 (ingest) → 形態學計算 (morphology) → 風場分析 (wind) → 風險評估 (risk) → API/地圖
```

## 資料流

1. **Ingest**: NLSC 建物、CWA 氣象、DEM 地形 → 清洗、座標轉換 → `data/processed/`
2. **Morphology**: 建物 + 網格 → FAI、BCR、SVF、z₀、zd → 網格屬性
3. **Wind**: FAI → 阻力面 → LCP 風廊；z₀/zd + 參考風速 → 對數剖面降尺度
4. **Risk**: 風速 + 形態學指標 → 風險等級（綠/黃/紅/黑）→ 風險分數
5. **Output**: PostGIS 儲存 → FastAPI 查詢 → MapLibre/Folium 視覺化

## 座標系統

所有內部計算使用 EPSG:3826（TWD97/TM2，公尺）。
API 輸出轉換為 EPSG:4326（WGS84）。
