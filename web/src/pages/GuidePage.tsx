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
          How to Use
        </h2>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Urban Turbulence Corridor (UTC) system user guide
        </p>
      </div>

      {/* What is UTC */}
      <Section title="What is UTC?">
        <p className="text-sm leading-relaxed text-gray-700 dark:text-gray-300">
          <strong>Urban Turbulence Corridor (UTC)</strong> is an urban wind risk assessment system
          designed for drone low-altitude operations. It integrates multi-source weather data,
          building morphology, terrain analysis, and airspace regulations to identify wind corridors
          and quantify turbulence risk across urban environments.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-lg bg-blue-50 p-3 dark:bg-blue-900/20">
            <Zap size={16} className="mb-1 text-blue-500" />
            <p className="text-xs font-semibold text-blue-800 dark:text-blue-300">Real-time Wind Data</p>
            <p className="text-xs text-blue-600 dark:text-blue-400">Open-Meteo + CWA weather stations</p>
          </div>
          <div className="rounded-lg bg-green-50 p-3 dark:bg-green-900/20">
            <Wind size={16} className="mb-1 text-green-500" />
            <p className="text-xs font-semibold text-green-800 dark:text-green-300">Wind Corridor Detection</p>
            <p className="text-xs text-green-600 dark:text-green-400">Minimum-cost pathfinding algorithm</p>
          </div>
          <div className="rounded-lg bg-purple-50 p-3 dark:bg-purple-900/20">
            <AlertTriangle size={16} className="mb-1 text-purple-500" />
            <p className="text-xs font-semibold text-purple-800 dark:text-purple-300">Drone Flyability</p>
            <p className="text-xs text-purple-600 dark:text-purple-400">5 DJI drone models supported</p>
          </div>
        </div>
      </Section>

      {/* Quick Start */}
      <Section title="Quick Start (3 Steps)">
        <ol className="space-y-3 text-sm text-gray-700 dark:text-gray-300">
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">1</span>
            <div>
              <strong>Check the Dashboard</strong> — View overall wind risk distribution, active corridors, and current wind statistics for the Taipei pilot area.
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">2</span>
            <div>
              <strong>Analyze Your Flight Area</strong> — Go to Flight Analysis, draw a polygon on the map around your planned flight zone, and get detailed wind/risk assessment.
            </div>
          </li>
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">3</span>
            <div>
              <strong>Check Drone Flyability</strong> — Select your drone model and flight height to see if conditions are safe for your specific aircraft.
            </div>
          </li>
        </ol>
      </Section>

      {/* Page Guide */}
      <Section title="Page Guide">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <PageCard
            to="/"
            icon={LayoutDashboard}
            title="Dashboard"
            description="Wind risk overview with stats cards, wind rose chart (16 directions), risk distribution, and interactive grid map. Shows real-time data from 1,470 grid cells."
          />
          <PageCard
            to="/analysis"
            icon={Navigation}
            title="Flight Analysis"
            description="Draw polygons for area analysis, set waypoints for route analysis, or plan optimal routes between two points. Supports 3 modes: safest, shortest, balanced."
          />
          <PageCard
            to="/corridors"
            icon={Wind}
            title="Wind Corridors"
            description="View identified wind corridors (primary rivers, secondary streets). Click a corridor to see wind speed, direction, and risk level details."
          />
          <PageCard
            to="/risk"
            icon={AlertTriangle}
            title="Risk Assessment"
            description="Color-coded risk map with drone flyability checker. Select your drone model (DJI Mini 4 Pro, Air 3, Mavic 3, Matrice 350/30) and check if flight is safe."
          />
          <PageCard
            to="/fai"
            icon={BarChart3}
            title="FAI Analysis"
            description="Frontal Area Index scatter plot: terrain roughness vs. FAI value. Higher FAI = denser buildings = more turbulence. Blue (open) to Red (dense urban)."
          />
          <PageCard
            to="/monitor"
            icon={Activity}
            title="System Monitor"
            description="Real-time health check for database, Open-Meteo API, and CWA weather API. Shows latency, status, and data counts."
          />
        </div>
      </Section>

      {/* Risk Levels */}
      <Section title="Risk Level Reference">
        <div className="space-y-2">
          <RiskBadge level="green" label="Safe for most drones" speed="<= 5 m/s" />
          <RiskBadge level="yellow" label="Caution — moderate wind" speed="5 ~ 8 m/s" />
          <RiskBadge level="red" label="High risk — enterprise drones only" speed="8 ~ 12 m/s" />
          <RiskBadge level="black" label="No-fly — exceeds all drone limits" speed="> 12 m/s" />
        </div>
        <p className="mt-3 text-xs text-gray-500 dark:text-gray-400">
          Wind speeds are measured at 3 height layers: 50m, 80m, and 120m AGL (Above Ground Level).
          Height correction uses power-law wind profile with urban roughness parameters.
        </p>
      </Section>

      {/* API Documentation */}
      <Section title="API Endpoints">
        <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">
          Base URL: <code className="rounded bg-gray-100 px-1.5 py-0.5 dark:bg-gray-700">/api/v1</code>
          &nbsp;&middot;&nbsp;
          <a href="/api/v1/docs" target="_blank" rel="noreferrer" className="text-blue-500 hover:underline">
            Interactive Docs (Swagger) <ExternalLink size={12} className="mb-0.5 inline" />
          </a>
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="text-xs font-semibold text-gray-500 dark:text-gray-400">
                <th className="pb-2 pr-3">Method</th>
                <th className="pb-2 pr-3">Endpoint</th>
                <th className="pb-2">Description</th>
              </tr>
            </thead>
            <tbody>
              <ApiRow method="GET" path="/wind?lon=&lat=&height=" desc="Query wind speed at a point" />
              <ApiRow method="GET" path="/corridors?city=taipei" desc="List wind corridors" />
              <ApiRow method="GET" path="/stats" desc="Dashboard summary statistics" />
              <ApiRow method="GET" path="/grids?height=50" desc="All grid cells for map rendering" />
              <ApiRow method="GET" path="/wind-rose" desc="16-sector wind rose data" />
              <ApiRow method="GET" path="/risk?lon=&lat=&height=&drone_id=" desc="Risk assessment with drone check" />
              <ApiRow method="GET" path="/fai?height=50" desc="Frontal Area Index data" />
              <ApiRow method="GET" path="/forecast?city=taipei&hours=72" desc="Hourly wind forecast (up to 7 days)" />
              <ApiRow method="GET" path="/forecast/stations?region=taipei" desc="CWA weather station observations" />
              <ApiRow method="POST" path="/area/predict" desc="Area polygon wind analysis" />
              <ApiRow method="POST" path="/route/analyze" desc="Route waypoint wind analysis" />
              <ApiRow method="POST" path="/route/plan" desc="Optimal route planning (3 modes)" />
              <ApiRow method="GET" path="/monitor" desc="System health check" />
            </tbody>
          </table>
        </div>
      </Section>

      {/* Data Sources */}
      <Section title="Data Sources">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">Open-Meteo</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Hourly wind speed/direction at 10m, 80m, 120m. Historical archive + 7-day forecast.
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">CWA (Central Weather Administration)</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Real-time automatic weather station observations. 9 stations in Taipei area.
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">ESA WorldCover</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              10m resolution land use classification for terrain roughness estimation.
            </p>
          </div>
          <div className="rounded-lg border border-gray-200 p-3 dark:border-gray-700">
            <p className="text-sm font-semibold text-gray-800 dark:text-gray-200">GHS-BUILT-H (JRC)</p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              100m resolution building height data for FAI (Frontal Area Index) computation.
            </p>
          </div>
        </div>
      </Section>
    </div>
  );
}
