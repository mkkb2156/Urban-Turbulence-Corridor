import { FlaskConical } from 'lucide-react';
import { useTestResults } from '../api/hooks';
import TestOverview from '../components/test-dashboard/TestOverview';
import TestResultCard from '../components/test-dashboard/TestResultCard';
import CoverageBar from '../components/test-dashboard/CoverageBar';
import TestRunner from '../components/test-dashboard/TestRunner';

export default function TestDashboardPage() {
  const { data: results, isLoading } = useTestResults();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
            <FlaskConical size={24} className="text-purple-500" />
            Test Dashboard
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Combined backend (pytest) and frontend (vitest) test results
          </p>
        </div>
        <TestRunner />
      </div>

      {/* Overview stats */}
      <TestOverview results={results} isLoading={isLoading} />

      {/* Test suites */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
          Test Suites
        </h3>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="h-4 w-48 rounded bg-gray-200 dark:bg-gray-700" />
                <div className="mt-2 h-3 w-32 rounded bg-gray-200 dark:bg-gray-700" />
              </div>
            ))}
          </div>
        ) : results ? (
          <div className="space-y-3">
            {results.suites.map((suite) => (
              <TestResultCard key={suite.name} suite={suite} />
            ))}
          </div>
        ) : (
          <div className="card text-center text-sm text-gray-500">
            No test results available. Click "Run All Tests" to start.
          </div>
        )}
      </div>

      {/* Coverage */}
      {results && results.coverage.length > 0 && (
        <div className="card">
          <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
            Code Coverage
          </h3>
          <div className="space-y-0.5">
            {results.coverage.map((mod) => (
              <CoverageBar key={mod.name} module={mod} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
