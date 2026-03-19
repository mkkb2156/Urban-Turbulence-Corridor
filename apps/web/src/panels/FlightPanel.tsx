import { X, Download, Wind, Battery, Clock, AlertTriangle } from "lucide-react";
import { useMapStore } from "@/store/map";
import { useFlightStore } from "@/store/flight";
import { useUIStore } from "@/store/ui";
import { useFlightSummary } from "@/api/hooks/useFlightSummary";
import { getRiskColor, getRiskLabel } from "@/utils/riskColor";
import type { RiskLevel } from "@/api/types";

const DRONE_CODE_MAP: Record<string, string> = {
  "dji-matrice30": "M30T",
  "dji-matrice350": "M350",
  "dji-mini4-pro": "Mini4",
  "dji-air3": "Air3",
  "dji-mavic3": "Mavic3E",
  "dji-matrice400": "M400",
};

export function FlightPanel() {
  const { flightPanelOpen, setFlightPanelOpen } = useUIStore();
  const selectedPoint = useMapStore((s) => s.selectedPoint);
  const { selectedDrone, selectedTime, altitude } = useFlightStore();

  const droneCode = DRONE_CODE_MAP[selectedDrone.id] ?? selectedDrone.id;

  const { data, isLoading } = useFlightSummary(
    selectedPoint && flightPanelOpen
      ? {
          lat: selectedPoint.lat,
          lng: selectedPoint.lng,
          drone: droneCode,
          datetime: selectedTime.toISOString(),
          altitude,
        }
      : null,
  );

  if (!flightPanelOpen) return null;

  const riskLevel: RiskLevel = (data?.risk_level as RiskLevel) ?? "yellow";

  return (
    <div className="absolute top-14 right-0 bottom-12 z-20 w-96 bg-gray-900/95 backdrop-blur-sm border-l border-gray-700/50 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <div
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: getRiskColor(riskLevel) }}
          />
          <h2 className="text-lg font-semibold text-white">飛行評估</h2>
        </div>
        <button
          onClick={() => setFlightPanelOpen(false)}
          className="rounded-lg p-1 text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-48">
          <div className="animate-spin h-8 w-8 border-2 border-blue-400 border-t-transparent rounded-full" />
        </div>
      ) : data ? (
        <div className="p-4 space-y-4">
          {/* 風險等級大標 */}
          <div
            className="rounded-xl p-4 text-center"
            style={{
              backgroundColor: getRiskColor(riskLevel) + "20",
              borderColor: getRiskColor(riskLevel) + "40",
              borderWidth: 1,
            }}
          >
            <div
              className="text-2xl font-bold"
              style={{ color: getRiskColor(riskLevel) }}
            >
              {getRiskLabel(riskLevel)}
            </div>
            <div className="text-sm text-gray-400 mt-1">
              風險分數 {data.risk_score}/100
            </div>
          </div>

          {/* 座標資訊 */}
          {selectedPoint && (
            <div className="text-xs text-gray-500 text-center">
              {selectedPoint.lat.toFixed(4)}, {selectedPoint.lng.toFixed(4)} ·{" "}
              {altitude}m AGL
            </div>
          )}

          {/* 風速資訊 */}
          <div className="rounded-lg bg-gray-800/50 p-3 space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <Wind className="h-4 w-4 text-blue-400" />
              <span>風場狀態</span>
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              <div>
                <div className="text-lg font-semibold text-white">
                  {data.wind_speed}
                </div>
                <div className="text-xs text-gray-500">風速 m/s</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-white">
                  {data.wind_gust}
                </div>
                <div className="text-xs text-gray-500">陣風 m/s</div>
              </div>
              <div>
                <div className="text-lg font-semibold text-white">
                  {data.wind_direction_label}
                </div>
                <div className="text-xs text-gray-500">風向</div>
              </div>
            </div>
          </div>

          {/* 機型檢查 */}
          <div className="rounded-lg bg-gray-800/50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-300">
                {selectedDrone.name}
              </span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                  data.drone_ok
                    ? "bg-green-900/50 text-green-400"
                    : "bg-red-900/50 text-red-400"
                }`}
              >
                {data.drone_ok ? "安全" : "超過限制"}
              </span>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              安全限制 {data.drone_safe_limit} m/s
              {data.drone_ok ? " ✓" : " ✗"}
            </div>
          </div>

          {/* 電池影響 */}
          <div className="rounded-lg bg-gray-800/50 p-3 flex items-center gap-3">
            <Battery className="h-5 w-5 text-yellow-400" />
            <div>
              <div className="text-sm text-white">
                電池消耗 +{data.battery_extra_pct}%
              </div>
              <div className="text-xs text-gray-500">
                相較無風環境額外消耗
              </div>
            </div>
          </div>

          {/* 風廊警告 */}
          {data.in_corridor && data.corridor_warning && (
            <div className="rounded-lg bg-yellow-900/20 border border-yellow-600/30 p-3 flex items-start gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-400 shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-200">
                {data.corridor_warning}
              </div>
            </div>
          )}

          {/* 最佳飛行時段 */}
          <div className="rounded-lg bg-gray-800/50 p-3 space-y-2">
            <div className="flex items-center gap-2 text-sm text-gray-300">
              <Clock className="h-4 w-4 text-blue-400" />
              <span>今日飛行時段</span>
            </div>
            <div className="space-y-1">
              {data.best_windows.map((w, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded-md bg-gray-900/50 px-3 py-1.5"
                >
                  <span className="text-sm text-white font-mono">
                    {w.start} - {w.end}
                  </span>
                  <span
                    className="rounded-full px-2 py-0.5 text-xs"
                    style={{
                      backgroundColor:
                        getRiskColor(w.risk as RiskLevel) + "30",
                      color: getRiskColor(w.risk as RiskLevel),
                    }}
                  >
                    {getRiskLabel(w.risk as RiskLevel)}
                  </span>
                </div>
              ))}
              {data.worst_period && (
                <div className="flex items-center justify-between rounded-md bg-red-900/20 px-3 py-1.5">
                  <span className="text-sm text-white font-mono">
                    {data.worst_period.start} - {data.worst_period.end}
                  </span>
                  <span className="rounded-full bg-red-900/50 px-2 py-0.5 text-xs text-red-400">
                    危險
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* 報告下載 */}
          <button className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500 transition-colors">
            <Download className="h-4 w-4" />
            下載飛行計畫報告
          </button>
        </div>
      ) : (
        <div className="p-4 text-center text-gray-400 text-sm">
          點擊地圖選擇位置
        </div>
      )}
    </div>
  );
}
