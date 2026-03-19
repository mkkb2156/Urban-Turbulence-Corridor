import type { RiskLevel } from "@/api/types";

export const RISK_COLORS: Record<RiskLevel, string> = {
  green: "#22c55e",
  yellow: "#eab308",
  red: "#ef4444",
  black: "#1e1e1e",
};

export const WIND_COLOR_RAMP = [
  { value: 0, color: [50, 136, 189] },
  { value: 3, color: [153, 213, 148] },
  { value: 6, color: [230, 245, 152] },
  { value: 9, color: [254, 224, 139] },
  { value: 12, color: [252, 141, 89] },
  { value: 15, color: [213, 62, 79] },
] as const;

export function getRiskColor(level: RiskLevel): string {
  return RISK_COLORS[level] ?? "#cccccc";
}

export function getRiskLabel(level: RiskLevel): string {
  const labels: Record<RiskLevel, string> = {
    green: "安全飛行",
    yellow: "注意飛行",
    red: "危險",
    black: "禁止飛行",
  };
  return labels[level] ?? "未知";
}

export function getRiskEmoji(level: RiskLevel): string {
  const emojis: Record<RiskLevel, string> = {
    green: "\u{1F7E2}",
    yellow: "\u{1F7E1}",
    red: "\u{1F534}",
    black: "\u{26AB}",
  };
  return emojis[level] ?? "\u{26AA}";
}
