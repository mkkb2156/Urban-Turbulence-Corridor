import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, MinusCircle, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import type { TestSuite, TestStatus } from '../../api/types';
import { TEST_STATUS_COLORS } from '../../utils/colors';
import { formatDuration } from '../../utils/format';

interface TestResultCardProps {
  suite: TestSuite;
}

function StatusIcon({ status }: { status: TestStatus }) {
  const iconProps = { size: 14 };
  switch (status) {
    case 'passed':
      return <CheckCircle {...iconProps} style={{ color: TEST_STATUS_COLORS.passed }} />;
    case 'failed':
      return <XCircle {...iconProps} style={{ color: TEST_STATUS_COLORS.failed }} />;
    case 'skipped':
      return <MinusCircle {...iconProps} style={{ color: TEST_STATUS_COLORS.skipped }} />;
    case 'error':
      return <AlertCircle {...iconProps} style={{ color: TEST_STATUS_COLORS.error }} />;
  }
}

export default function TestResultCard({ suite }: TestResultCardProps) {
  const [expanded, setExpanded] = useState(suite.failed > 0);

  const total = suite.passed + suite.failed + suite.skipped;
  const passRate = total > 0 ? (suite.passed / total) * 100 : 0;

  return (
    <div
      className="card overflow-hidden"
      data-testid={`test-suite-${suite.name}`}
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center gap-3 text-left"
      >
        {expanded ? (
          <ChevronDown size={16} className="shrink-0 text-gray-400" />
        ) : (
          <ChevronRight size={16} className="shrink-0 text-gray-400" />
        )}

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">
              {suite.name}
            </span>
            <span
              className={clsx(
                'rounded px-1.5 py-0.5 text-xs font-medium',
                suite.framework === 'pytest'
                  ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300'
                  : 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
              )}
            >
              {suite.framework}
            </span>
          </div>
          <div className="mt-0.5 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
            <span style={{ color: TEST_STATUS_COLORS.passed }}>
              {suite.passed} 通過
            </span>
            {suite.failed > 0 && (
              <span style={{ color: TEST_STATUS_COLORS.failed }}>
                {suite.failed} 失敗
              </span>
            )}
            {suite.skipped > 0 && (
              <span style={{ color: TEST_STATUS_COLORS.skipped }}>
                {suite.skipped} 跳過
              </span>
            )}
            <span>{formatDuration(suite.duration)}</span>
          </div>
        </div>

        {/* Pass rate bar */}
        <div className="flex w-24 items-center gap-2">
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-600">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${passRate}%`,
                backgroundColor:
                  passRate === 100
                    ? TEST_STATUS_COLORS.passed
                    : passRate >= 80
                      ? TEST_STATUS_COLORS.skipped
                      : TEST_STATUS_COLORS.failed,
              }}
            />
          </div>
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
            {passRate.toFixed(0)}%
          </span>
        </div>
      </button>

      {/* Expanded test list */}
      {expanded && (
        <div className="mt-3 border-t border-gray-100 pt-3 dark:border-gray-700">
          <ul className="space-y-1">
            {suite.tests.map((test) => (
              <li
                key={test.name}
                className="flex items-start gap-2 rounded px-2 py-1 text-sm hover:bg-gray-50 dark:hover:bg-gray-700/50"
              >
                <StatusIcon status={test.status} />
                <div className="flex-1">
                  <span className="text-gray-700 dark:text-gray-200">
                    {test.name}
                  </span>
                  {test.error_message && (
                    <pre className="mt-1 overflow-x-auto rounded bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-300">
                      {test.error_message}
                    </pre>
                  )}
                </div>
                <span className="shrink-0 text-xs text-gray-400">
                  {formatDuration(test.duration)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
