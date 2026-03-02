import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import DashboardPage from './pages/DashboardPage';
import CorridorPage from './pages/CorridorPage';
import RiskPage from './pages/RiskPage';
import FAIPage from './pages/FAIPage';
import TestDashboardPage from './pages/TestDashboardPage';

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/corridors" element={<CorridorPage />} />
        <Route path="/risk" element={<RiskPage />} />
        <Route path="/fai" element={<FAIPage />} />
        <Route path="/tests" element={<TestDashboardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
