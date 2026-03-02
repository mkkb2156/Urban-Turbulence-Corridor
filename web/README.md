# UTC Web - Urban Turbulence Corridor Dashboard

Frontend dashboard for the Urban Turbulence Corridor (UTC) project — a Taiwan urban wind corridor mapping system for drone risk assessment.

## Technology Stack

- **React 18** with TypeScript
- **Vite** for bundling and dev server
- **Vitest** for unit and component testing
- **MapLibre GL JS** for map rendering
- **TailwindCSS** for styling
- **React Router** for navigation
- **TanStack React Query** for API data fetching
- **Recharts** for charts
- **Lucide React** for icons

## Getting Started

```bash
# Install dependencies
npm install

# Start development server (proxies /api/* to localhost:8000)
npm run dev

# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage

# Build for production
npm run build
```

## Project Structure

```
src/
  api/         - API client, TypeScript types, React Query hooks
  components/  - Reusable UI components
    map/       - MapLibre map, controls, legend, popup
    dashboard/ - Stats cards, wind rose chart, risk distribution
    drone/     - Drone flyability checker
    test-dashboard/ - Test results viewer
  pages/       - Route-level page components
  utils/       - Color mappings, formatters, geo helpers
  __tests__/   - Vitest test files
```

## Available Pages

| Path | Description |
|------|-------------|
| `/` | Dashboard with map overview and stats |
| `/corridors` | Wind corridor detail viewer |
| `/risk` | Risk assessment tool + drone check |
| `/fai` | Frontal Area Index visualization |
| `/tests` | Combined backend/frontend test results |

## API Proxy

The Vite dev server proxies all `/api/*` requests to `http://localhost:8000` (FastAPI backend). Ensure the backend is running before using API-dependent features.

## Risk Levels

| Level | Color | Chinese | English |
|-------|-------|---------|---------|
| green | #2ecc71 | 安全 | Safe |
| yellow | #f1c40f | 注意 | Caution |
| red | #e74c3c | 危險 | Danger |
| black | #2c3e50 | 極度危險 | Extreme |
