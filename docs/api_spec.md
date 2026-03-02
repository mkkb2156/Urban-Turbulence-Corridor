# UTC API 規格

Base URL: `http://localhost:8000/api/v1`

## Endpoints

### POST /wind
查詢指定座標的估算風速。

**Request Body:**
```json
{
  "lon": 121.55,
  "lat": 25.03,
  "height": 50.0
}
```

**Response:**
```json
{
  "grid_id": "taipei_042_078",
  "wind_speed": 6.5,
  "wind_direction": "NE",
  "risk_level": "yellow",
  "risk_label": "注意",
  "risk_score": 55.0
}
```

### POST /risk
查詢指定座標的風險等級（含無人機可飛性評估）。

### GET /corridors?city=taipei
查詢某城市的風廊多邊形。

### GET /health
健康檢查。
