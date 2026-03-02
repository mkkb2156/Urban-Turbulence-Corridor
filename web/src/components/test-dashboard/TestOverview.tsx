import type { LucideIcon } from 'lucide-react';
import { CheckCircle, XCircle, MinusCircle, Clock } from 'lucide-react';
import clsx from 'clsx';
import type { TestResults } from '../../api/types';
import { TEST_STATUS_COLORS } from '../../utils/colors';
import { formatDuration, formatDateTime } from '../../utils/format';

interface TestOverviewProps {
  results?: TestResults;
  isLoading?: boolean;
}

interface OverviewStat {
  label: string;
  value: number;
  color: string;
  icon: LucideIcon;
}

export default function TestOverview({ results, isLoading }: TestOverviewProps) {
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="mb-2 h-4 w-20 rounded bg-gray-200 dark:bg-gray-700" />
            <div className="h-8 w-12 rounded bg-gray-200 dark:bg-gray-700" />
          </div>
        ))}
      </div>
    );
  }

  if (!results) return null;

  const backendSuites = results.suites.filter((s) => s.framework === 'pytest');
  const frontendSuites = results.suites.filter((s) => s.framework === 'vitest');

  const backendPassed = backendSuites.reduce((s, suite) => s + suite.passed, 0);
  const backendFailed = backendSuites.reduce((s, suite) => s + suite.failed, 0);
  const frontendPassed = frontendSuites.reduce((s, suite) => s + suite.passed, 0);
  const frontendFailed = frontendSuites.reduce((s, suite) => s + suite.failed, 0);

  const stats: OverviewStat[] = [
    {
      label: 'Passed',
      value: results.total_passed,
      color: TEST_STATUS_COLORS.passed,
      icon: CheckCircle,
    },
    {
      label: 'Failed',
      value: results.total_failed,
      color: TEST_STATUS_COLORS.failed,
      icon: XCircle,
    },
    {
      label: 'Skipped',
      value: results.total_skipped,
      color: TEST_STATUS_COLORS.skipped,
      icon: MinusCircle,
    },
    {
      label: 'Duration',
      value: results.total_duration,
      color: '#6b7280',
      icon: Clock,
    },
  ];

  return (
    <div>
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4" data-testid="test-overview">
        {stats.map((stat) => (
          <div key={stat.label} className="card">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {stat.label}
                </p>
                <p
                  className="mt-1 text-2xl font-bold"
                  style={{ color: stat.color }}
                >
                  {stat.label === 'Duration'
                    ? formatDuration(stat.value)
                    : stat.value}
                </p>
              </div>
              <stat.icon size={20} color={stat.color} />
            </div>
          </div>
        ))}
      </div>

      {/* Backend vs Frontend breakdown */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div className="card">
          <h4 className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400">
            Backend (pytest)
          </h4>
          <div className="flex items-baseline gap-4">
            <span className="text-xl font-bold" style={{ color: TEST_STATUS_COLORS.passed }}>
              {backendPassed}
            </span>
            <span className="text-sm text-gray-500">passed</span>
            {backendFailed > 0 && (
              <>
                <span className="text-xl font-bold" style={{ color: TEST_STATUS_COLORS.failed }}>
                  {backendFailed}
                </span>
                <span className="text-sm text-gray-500">failed</span>
              </>
            )}
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-600">
            <div
              className={clsx(
                'h-full rounded-full',
                backendFailed === 0 ? 'bg-risk-green' : 'bg-risk-red',
              )}
              style={{
                width: `${
                  backendPassed + backendFailed > 0
                    ? (backendPassed / (backendPassed + backendFailed)) * 100
                    : 0
                }%`,
              }}
            />
          </div>
        </div>

        <div className="card">
          <h4 className="mb-2 text-xs font-semibold text-gray-500 dark:text-gray-400">
            Frontend (vitest)
          </h4>
          <div className="flex items-baseline gap-4">
            <span className="text-xl font-bold" style={{ color: TEST_STATUS_COLORS.passed }}>
              {frontendPassed}
            </span>
            <span className="text-sm text-gray-500">passed</span>
            {frontendFailed > 0 && (
              <>
                <span className="text-xl font-bold" style={{ color: TEST_STATUS_COLORS.failed }}>
                  {frontendFailed}
                </span>
                <span className="text-sm text-gray-500">failed</span>
              </>
            )}
          </div>
          <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-600">
            <div
              className={clsx(
                'h-full rounded-full',
                frontendFailed === 0 ? 'bg-risk-green' : 'bg-risk-red',
              )}
              style={{
                width: `${
                  frontendPassed + frontendFailed > 0
                    ? (frontendPassed / (frontendPassed + frontendFailed)) * 100
                    : 0
                }%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Last run timestamp */}
      {results.last_run && (
        <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">
          Last run: {formatDateTime(results.last_run)}
        </p>
      )}
    </div>
  );
}
