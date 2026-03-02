import clsx from 'clsx';
import type { CoverageModule } from '../../api/types';

interface CoverageBarProps {
  module: CoverageModule;
}

function getCoverageColor(percentage: number): string {
  if (percentage >= 80) return 'bg-risk-green';
  if (percentage >= 60) return 'bg-risk-yellow';
  return 'bg-risk-red';
}

function getCoverageTextColor(percentage: number): string {
  if (percentage >= 80) return 'text-green-700 dark:text-green-400';
  if (percentage >= 60) return 'text-yellow-700 dark:text-yellow-400';
  return 'text-red-700 dark:text-red-400';
}

export default function CoverageBar({ module }: CoverageBarProps) {
  return (
    <div className="flex items-center gap-3 py-1.5" data-testid={`coverage-${module.name}`}>
      <span className="w-40 truncate text-sm text-gray-700 dark:text-gray-200" title={module.name}>
        {module.name}
      </span>

      <div className="flex flex-1 items-center gap-2">
        <div className="h-2 flex-1 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-600">
          <div
            className={clsx('h-full rounded-full transition-all', getCoverageColor(module.percentage))}
            style={{ width: `${Math.min(module.percentage, 100)}%` }}
          />
        </div>
        <span
          className={clsx(
            'w-12 text-right text-xs font-semibold',
            getCoverageTextColor(module.percentage),
          )}
        >
          {module.percentage.toFixed(1)}%
        </span>
      </div>

      <div className="hidden gap-3 text-xs text-gray-400 dark:text-gray-500 sm:flex">
        <span title="Statements">S: {module.statements}%</span>
        <span title="Branches">B: {module.branches}%</span>
        <span title="Functions">F: {module.functions}%</span>
        <span title="Lines">L: {module.lines}%</span>
      </div>
    </div>
  );
}
