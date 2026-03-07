import {
  BookOpen,
  LayoutDashboard,
  Navigation,
  Wind,
  AlertTriangle,
  BarChart3,
  Activity,
  ExternalLink,
  Zap,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import clsx from 'clsx';

/* ─── Section wrapper ────────────────────────────────────────── */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="card">
      <h3 className="mb-4 text-base font-bold text-gray-900 dark:text-white">{title}</h3>
      {children}
    </section>
  );
}

/* ─── Risk badge ─────────────────────────────────────────────── */
function RiskBadge({ level, label, speed }: { level: string; label: string; speed: string }) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    yellow: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    red: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    black: 'bg-gray-800 text-white dark:bg-gray-600',
  };
  return (
    <div className={clsx('flex items-center justify-between rounded-lg px-4 py-3', colorMap[level])}>
      <div>
        <span className="text-sm font-bold uppercase">{level}</span>
        <span className="ml-2 text-sm">{label}</span>
      </div>
      <span className="font-mono text-sm">{speed}</span>
    </div>
  );
}

/* ─── Page link card ─────────────────────────────────────────── */
function PageCard({
  to,
  icon: Icon,
  title,
  description,
}: {
  to: string;
  icon: React.ElementType;
  title: string;
  description: string;
}) {
  return (
    <Link
      to={to}
      className="card group flex gap-4 transition-shadow hover:shadow-md"
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
        <Icon size={20} />
      </div>
      <div>
        <h4 className="text-sm font-semibold text-gray-900 group-hover:text-blue-600 dark:text-white dark:group-hover:text-blue-400">
          {title}
        </h4>
        <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">{description}</p>
      </div>
    </Link>
  );
}

/* ─── API endpoint row ───────────────────────────────────────── */
function ApiRow({ method, path, desc }: { method: string; path: string; desc: string }) {
  return (
    <tr className="border-t border-gray-100 dark:border-gray-700">
      <td className="py-2 pr-3">
        <span className={clsx(
          'rounded px-1.5 py-0.5 text-xs font-bold',
          method === 'GET' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' : 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300',
        )}>
          {method}
        </span>
      </td>
      <td className="py-2 pr-3 font-mono text-xs text-gray-700 dark:text-gray-300">{path}</td>
      <td className="py-2 text-xs text-gray-500 dark:text-gray-400">{desc}</td>
    </tr>
  );
}

/* ─── Main Page ──────────────────────────────────────────────── */
export default function GuidePage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
          <BookOpen size={24} className="text-indigo-500" />
          使用指南
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          城市風廊系統 (UTC) 使用者指南
        </p>
      </div>

      {/* What is UTC */}
      <Section title="什麼是 UTC？">
        <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
          城市風廊系統 (Urban Turbulence Corridor, UTC) 是專為無人機低空飛行設計的城市風險評估系統。整合多源氣象資料、建築形態、地形分析與空域法規，識別風廊並量化城市環境中的亂流風險。
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-900/20">
            <Zap size={16} className="mb-1 text-blue-500" />
            <p className="text-xs font-semibold text-blue-800 dark:text-blue-300">即時風場資料</p>
            <p className="text-xs text-blue-600 dark:text-blue-400">Open-Meteo + 中央氣象署測站</p>
          </div>
          <div className="rounded-lg bg-green-50 p-3 dark:bg-green-900/20">
            <Wind size={16} className="mb-1 text-green-500" />
            <p className="text-xs font-semibold text-green-800 dark:text-green-300">風廊偵測</p>
            <p className="text-xs text-green-600 dark:text-green-400">最小成本路徑演算法</p>
          </div>
          <div className="rounded-lg bg-purple-50 p-3 dark:bg-purple-900/20">
            <AlertTriangle size={16} className="mb-1 text-purple-500" />
            <p className="text-xs font-semibold text-purple-800 dark:text-purple-300">無人機適飛評估</p>
            <p className="text-xs text-purple-600 dark:text-purple-400">支援 5 款 DJI 機型</p>
          </div>
        </div>
      </Section>

      {/* Quick Start */}
      <Section title="快速開始（3 步驟）">
        <ol className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">1</span>
            <div>
              <strong>查看儀表板</strong> — 瀏覽整體風險分布、活躍風廊及台北試驗區域的即時風速統計。
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">2</span>
            <div>
              <strong>分析飛行區域</strong> — 前往飛行分析頁面，在地圖上繪製多邊形圈選計畫飛行區域，取得詳細的風場與風險評估。
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">3</span>
            <div>
              <strong>檢查無人機適飛性</strong> — 選擇無人機機型與飛行高度，確認目前條件是否適合該機型飛行。
            </div>
          </li>
        </ol>
      </Section>

      {/* Page Guide */}
      <Section title="頁面導覽">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <PageCard
            to="/"
            icon={LayoutDashboard}
            title="儀表板"
            description="風險總覽，包含統計卡片、風花圖（16 方位）、風險分布及互動式網格地圖。顯示 1,470 個網格的即時資料。"
          />
          <PageCard
            to="/analysis"
            icon={Navigation}
            title="飛行分析"
            description="繪製多邊形進行區域分析、設定航點進行路線分析，或規劃兩點間最佳路線。支援 3 種模式：最安全、最短、平衡。"
          />
          <PageCard
            to="/corridors"
            icon={Wind}
            title="風廊"
            description="檢視已識別的風廊（主要河道、次要街道）。點擊風廊可查看風速、風向及風險等級詳情。"
          />
          <PageCard
            to="/risk"
            icon={AlertTriangle}
            title="風險評估"
            description="色碼風險地圖與無人機適飛檢查。選擇機型（DJI Mini 4 Pro、Air 3、Mavic 3、Matrice 350/30）並檢查是否可安全飛行。"
          />
          <PageCard
            to="/fai"
            icon={BarChart3}
            title="FAI 分析"
            description="正面面積指數散佈圖：地形粗糙度 vs FAI 值。FAI 越高 = 建築越密集 = 亂流越強。藍色（開闊）至紅色（密集都市）。"
          />
          <PageCard
            to="/monitor"
            icon={Activity}
            title="系統監控"
            description="即時健康檢查，包含資料庫、Open-Meteo API 及中央氣象署 API。顯示延遲、狀態及資料筆數。"
          />
        </div>
      </Section>

      {/* Risk Levels */}
      <Section title="風險等級對照表">
        <div className="space-y-2">
          <RiskBadge level="green" label="大多數無人機可安全飛行" speed="<= 5 m/s" />
          <RiskBadge level="yellow" label="注意 — 中等風速" speed="5 ~ 8 m/s" />
          <RiskBadge level="red" label="高風險 — 僅限企業級無人機" speed="8 ~ 12 m/s" />
          <RiskBadge level="black" label="禁飛 — 超過所有無人機限制" speed="> 12 m/s" />
        </div>
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          風速於 3 個高度層進行量測：50m、80m、120m AGL（地面以上高度）。高度修正採用冪律風廓線搭配都市粗糙度參數。
        </p>
      </Section>

      {/* API Documentation */}
      <Section title="API 端點">
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
          Base URL: <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-700">/api/v1</code>
          &nbsp;&middot;&nbsp;
          <a href="/api/v1/docs" target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
            互動式文件 (Swagger) <ExternalLink size={12} className="mb-0.5 inline" />
          </a>
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                <th className="pb-2 pr-3">方法</th>
                <th className="pb-2 pr-3">端點</th>
                <th className="pb-2">說明</th>
              </tr>
            </thead>
            <tbody>
              <ApiRow method="GET" path="/wind?lon=&lat=&height=" desc="查詢指定點風速" />
              <ApiRow method="GET" path="/corridors?city=taipei" desc="列出風廊" />
              <ApiRow method="GET" path="/stats" desc="儀表板摘要統計" />
              <ApiRow method="GET" path="/grids?height=50" desc="地圖渲染用網格資料" />
              <ApiRow method="GET" path="/wind-rose" desc="16 方位風花圖資料" />
              <ApiRow method="GET" path="/risk?lon=&lat=&height=&drone_id=" desc="風險評估含無人機檢查" />
              <ApiRow method="GET" path="/fai?height=50" desc="正面面積指數資料" />
              <ApiRow method="GET" path="/forecast?city=taipei&hours=72" desc="逐時風速預報（最多 7 天）" />
              <ApiRow method="GET" path="/forecast/stations?region=taipei" desc="中央氣象署測站觀測資料" />
              <ApiRow method="POST" path="/area/predict" desc="區域多邊形風場分析" />
              <ApiRow method="POST" path="/route/analyze" desc="航線航點風場分析" />
              <ApiRow method="POST" path="/route/plan" desc="最佳路線規劃（3 種模式）" />
              <ApiRow method="GET" path="/monitor" desc="系統健康檢查" />
            </tbody>
          </table>
        </div>
      </Section>

      {/* Data Sources */}
      <Section title="資料來源">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">Open-Meteo</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              10m、80m、120m 逐時風速／風向。歷史資料庫 + 7 天預報。
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">中央氣象署 (CWA)</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              即時自動氣象站觀測資料。台北地區 9 個測站。
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">ESA WorldCover</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              10m 解析度土地利用分類，用於地形粗糙度估算。
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">GHS-BUILT-H (JRC)</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              100m 解析度建築高度資料，用於 FAI（正面面積指數）計算。
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}
