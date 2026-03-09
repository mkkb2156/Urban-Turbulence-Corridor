import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import TestResultCard from '../../components/test-dashboard/TestResultCard';
import type { TestSuite } from '../../api/types';

const mockPassingSuite: TestSuite = {
  name: 'test_wind_api',
  framework: 'pytest',
  tests: [
    { name: 'test_get_wind_speed', status: 'passed', duration: 120 },
    { name: 'test_get_wind_direction', status: 'passed', duration: 85 },
    { name: 'test_invalid_coordinates', status: 'passed', duration: 45 },
  ],
  passed: 3,
  failed: 0,
  skipped: 0,
  duration: 250,
};

const mockFailingSuite: TestSuite = {
  name: 'components/WindMap',
  framework: 'vitest',
  tests: [
    { name: 'renders map container', status: 'passed', duration: 200 },
    {
      name: 'handles click on grid cell',
      status: 'failed',
      duration: 350,
      error_message: 'Expected element to be visible, but it was not',
    },
    { name: 'shows loading indicator', status: 'skipped', duration: 0 },
  ],
  passed: 1,
  failed: 1,
  skipped: 1,
  duration: 550,
};

describe('TestResultCard', () => {
  it('should render the suite name', () => {
    render(<TestResultCard suite={mockPassingSuite} />);
    expect(screen.getByText('test_wind_api')).toBeInTheDocument();
  });

  it('should render the framework badge', () => {
    render(<TestResultCard suite={mockPassingSuite} />);
    expect(screen.getByText('pytest')).toBeInTheDocument();
  });

  it('should render vitest badge for frontend suites', () => {
    render(<TestResultCard suite={mockFailingSuite} />);
    expect(screen.getByText('vitest')).toBeInTheDocument();
  });

  it('should display pass/fail/skip counts', () => {
    render(<TestResultCard suite={mockFailingSuite} />);
    expect(screen.getByText(/1\s*通過/)).toBeInTheDocument();
    expect(screen.getByText(/1\s*失敗/)).toBeInTheDocument();
    expect(screen.getByText(/1\s*跳過/)).toBeInTheDocument();
  });

  it('should show 100% pass rate for fully passing suite', () => {
    render(<TestResultCard suite={mockPassingSuite} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('should auto-expand suites with failures', () => {
    render(<TestResultCard suite={mockFailingSuite} />);
    // Should show individual test names because failed suites auto-expand
    expect(screen.getByText('renders map container')).toBeInTheDocument();
    expect(screen.getByText('handles click on grid cell')).toBeInTheDocument();
  });

  it('should show error message for failed tests', () => {
    render(<TestResultCard suite={mockFailingSuite} />);
    expect(
      screen.getByText('Expected element to be visible, but it was not'),
    ).toBeInTheDocument();
  });

  it('should toggle expansion on click', () => {
    render(<TestResultCard suite={mockPassingSuite} />);
    // Passing suite starts collapsed
    expect(screen.queryByText('test_get_wind_speed')).not.toBeInTheDocument();

    // Click to expand
    const button = screen.getByRole('button');
    fireEvent.click(button);

    expect(screen.getByText('test_get_wind_speed')).toBeInTheDocument();
    expect(screen.getByText('test_get_wind_direction')).toBeInTheDocument();
    expect(screen.getByText('test_invalid_coordinates')).toBeInTheDocument();
  });

  it('should display the suite duration', () => {
    render(<TestResultCard suite={mockPassingSuite} />);
    expect(screen.getByText('250ms')).toBeInTheDocument();
  });
});
