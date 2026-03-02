import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatsCards from '../../components/dashboard/StatsCards';
import type { DashboardStats } from '../../api/types';

const mockStats: DashboardStats = {
  total_grids: 1500,
  risk_distribution: {
    green: 800,
    yellow: 400,
    red: 200,
    black: 100,
  },
  corridor_count: 12,
  mean_wind_speed: 7.3,
  monitoring_area_km2: 45.2,
  last_updated: new Date().toISOString(),
};

describe('StatsCards', () => {
  it('should render the stats cards container', () => {
    render(<StatsCards stats={mockStats} />);
    expect(screen.getByTestId('stats-cards')).toBeInTheDocument();
  });

  it('should display grid cell count', () => {
    render(<StatsCards stats={mockStats} />);
    expect(screen.getByText('1.5K')).toBeInTheDocument();
  });

  it('should display mean wind speed', () => {
    render(<StatsCards stats={mockStats} />);
    expect(screen.getByText('7.3 m/s')).toBeInTheDocument();
  });

  it('should display corridor count', () => {
    render(<StatsCards stats={mockStats} />);
    expect(screen.getByText('12')).toBeInTheDocument();
  });

  it('should display monitoring area in subtext', () => {
    render(<StatsCards stats={mockStats} />);
    expect(screen.getByText(/45\.2 km/)).toBeInTheDocument();
  });

  it('should show loading skeletons when isLoading is true', () => {
    const { container } = render(<StatsCards isLoading />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('should render all four stat labels', () => {
    render(<StatsCards stats={mockStats} />);
    expect(screen.getByText('Grid Cells')).toBeInTheDocument();
    expect(screen.getByText('Mean Wind Speed')).toBeInTheDocument();
    expect(screen.getByText('Wind Corridors')).toBeInTheDocument();
    expect(screen.getByText('Last Updated')).toBeInTheDocument();
  });
});
