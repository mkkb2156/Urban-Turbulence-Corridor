import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FlyabilityChecker from '../../components/drone/FlyabilityChecker';

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
}

describe('FlyabilityChecker', () => {
  it('should render the component title', () => {
    renderWithProviders(<FlyabilityChecker />);
    expect(screen.getByText('無人機適飛檢查')).toBeInTheDocument();
  });

  it('should render the drone model dropdown', () => {
    renderWithProviders(<FlyabilityChecker />);
    const select = screen.getByRole('combobox');
    expect(select).toBeInTheDocument();
    expect(select).toHaveValue('dji-mini4-pro');
  });

  it('should list all drone models in the dropdown', () => {
    renderWithProviders(<FlyabilityChecker />);
    const options = screen.getAllByRole('option');
    expect(options).toHaveLength(5);
    expect(options[0]).toHaveTextContent('DJI Mini 4 Pro');
    expect(options[1]).toHaveTextContent('DJI Air 3');
    expect(options[2]).toHaveTextContent('DJI Mavic 3');
    expect(options[3]).toHaveTextContent('DJI Matrice 350 RTK');
    expect(options[4]).toHaveTextContent('DJI Matrice 30');
  });

  it('should render coordinate inputs with defaults', () => {
    renderWithProviders(<FlyabilityChecker />);
    const lonInput = screen.getByDisplayValue('121.55');
    const latInput = screen.getByDisplayValue('25.03');
    expect(lonInput).toBeInTheDocument();
    expect(latInput).toBeInTheDocument();
  });

  it('should render height selection buttons', () => {
    renderWithProviders(<FlyabilityChecker />);
    expect(screen.getByText('50m')).toBeInTheDocument();
    expect(screen.getByText('80m')).toBeInTheDocument();
    expect(screen.getByText('120m')).toBeInTheDocument();
  });

  it('should render the Check Flyability button', () => {
    renderWithProviders(<FlyabilityChecker />);
    expect(
      screen.getByRole('button', { name: '檢查適飛性' }),
    ).toBeInTheDocument();
  });

  it('should render labels for longitude and latitude', () => {
    renderWithProviders(<FlyabilityChecker />);
    expect(screen.getByText(/經度/)).toBeInTheDocument();
    expect(screen.getByText(/緯度/)).toBeInTheDocument();
  });
});
