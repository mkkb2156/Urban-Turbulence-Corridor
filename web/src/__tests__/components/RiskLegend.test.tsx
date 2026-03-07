import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import RiskLegend from '../../components/map/RiskLegend';

describe('RiskLegend', () => {
  it('should render all four risk levels', () => {
    render(<RiskLegend />);

    expect(screen.getByText('安全')).toBeInTheDocument();
    expect(screen.getByText('Safe')).toBeInTheDocument();
    expect(screen.getByText('注意')).toBeInTheDocument();
    expect(screen.getByText('Caution')).toBeInTheDocument();
    expect(screen.getByText('危險')).toBeInTheDocument();
    expect(screen.getByText('Danger')).toBeInTheDocument();
    expect(screen.getByText('極度危險')).toBeInTheDocument();
    expect(screen.getByText('Extreme')).toBeInTheDocument();
  });

  it('should render color swatches for each risk level', () => {
    render(<RiskLegend />);

    const greenSwatch = screen.getByTestId('risk-color-green');
    const yellowSwatch = screen.getByTestId('risk-color-yellow');
    const redSwatch = screen.getByTestId('risk-color-red');
    const blackSwatch = screen.getByTestId('risk-color-black');

    expect(greenSwatch).toHaveStyle({ backgroundColor: '#2ecc71' });
    expect(yellowSwatch).toHaveStyle({ backgroundColor: '#f1c40f' });
    expect(redSwatch).toHaveStyle({ backgroundColor: '#e74c3c' });
    expect(blackSwatch).toHaveStyle({ backgroundColor: '#2c3e50' });
  });

  it('should render the "風險等級" heading', () => {
    render(<RiskLegend />);
    expect(screen.getByText('風險等級')).toBeInTheDocument();
  });
});
