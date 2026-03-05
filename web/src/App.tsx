import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { FlightProvider } from './contexts/FlightContext';
import DashboardPage from './pages/DashboardPage';
import CorridorPage from './pages/CorridorPage';
import RiskPage from './pages/RiskPage';
import FAIPage from './pages/FAIPage';
import AnalysisPage from './pages/AnalysisPage';
import TestDashboardPage from './pages/TestDashboardPage';

function App() {
  return (
    <FlightProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/analysis" element={<AnalysisPage />} />
          <Route path="/corridors" element={<CorridorPage />} />
          <Route path="/risk" element={<RiskPage />} />
          <Route path="/fai" element={<FAIPage />} />
          <Route path="/tests" element={<TestDashboardPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </FlightProvider>
  );
}

export default App;
