"""任務報告匯出 API（JSON format for demo）。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from schemas import ReportRequest

router = APIRouter()


@router.post("/report/generate")
async def generate_report(req: ReportRequest):
    """生成任務報告（目前僅支援 JSON）。"""
    report = {
        "title": req.title,
        "report_type": req.report_type,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "drone_id": req.drone_id,
            "height": req.height,
            "format": req.format,
        },
        "summary": _generate_summary(req),
        "data": req.data,
        "recommendations": _generate_recommendations(req),
    }

    return JSONResponse(
        content=report,
        headers={
            "Content-Disposition": f'attachment; filename="utc_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json"',
        },
    )


def _generate_summary(req: ReportRequest) -> dict:
    """產生報告摘要。"""
    data = req.data
    summary = {"report_type": req.report_type}

    if req.report_type == "area":
        summary.update({
            "area_km2": data.get("area_km2", 0),
            "grid_count": data.get("grid_count", 0),
            "mean_wind_speed": data.get("wind_stats", {}).get("mean_speed", 0),
            "max_wind_speed": data.get("wind_stats", {}).get("max_speed", 0),
            "risk_distribution": data.get("risk_distribution", {}),
        })
    elif req.report_type in ("route", "plan"):
        summary.update({
            "total_distance_m": data.get("total_distance_m", 0),
            "total_time_s": data.get("total_time_s", 0),
            "max_risk": data.get("max_risk", "unknown"),
            "avg_wind_speed": data.get("avg_wind_speed", 0),
            "segment_count": len(data.get("segments", [])),
        })

    return summary


def _generate_recommendations(req: ReportRequest) -> list[str]:
    """基於數據產生飛行建議。"""
    recs = []
    data = req.data

    max_risk = data.get("max_risk", "green")
    if max_risk == "black":
        recs.append("區域/路線存在極度危險風速(>12 m/s)，強烈建議取消飛行任務")
    elif max_risk == "red":
        recs.append("存在高風險區段(8-12 m/s)，僅建議工業級無人機執行任務")
    elif max_risk == "yellow":
        recs.append("部分區段風速偏高(5-8 m/s)，消費級無人機需謹慎操作")
    else:
        recs.append("風況良好，適合所有機型飛行")

    if req.drone_id:
        flyability = data.get("flyability", {})
        if flyability and not flyability.get("flyable", True):
            recs.append(f"所選無人機({req.drone_id})在當前風況下存在安全風險，建議更換更高抗風等級機型")

    if req.height >= 100:
        recs.append("飛行高度較高，高空風速通常更強，請密切關注風速變化")

    recs.append("建議起飛前再次確認即時風場數據")

    return recs
