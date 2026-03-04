# 資料來源與下載

大型檔案不納入 Git，請自行下載後放在專案目錄或 `data/raw/`。

## 台灣 OSM 圖資（.osm.pbf）

- **下載**：[Geofabrik Taiwan 每日更新](https://download.geofabrik.de/asia/taiwan-latest.osm.pbf)（約 280–300MB）
- **使用方式**：下載後將檔名改為或連結為 `taiwan-260302.osm.pbf`（或專案/腳本所預期的檔名），放在專案根目錄或 `data/raw/`。
- **說明**：Geofabrik 每日更新，可依需要重新下載取得最新圖資。

## DSM / DTM 網格 metadata

- 專案內已包含 2024/2025 年版全臺灣 20m 網格數值地形模型 DSM/DTM 的 **metadata CSV**（清單與下載連結由內政部國土測繪中心等提供），無需額外下載即可查詢。
