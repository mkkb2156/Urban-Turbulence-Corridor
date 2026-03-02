import { useState, useEffect, useCallback } from 'react';
import { Outlet } from 'react-router-dom';
import { Moon, Sun } from 'lucide-react';
import clsx from 'clsx';
import Sidebar from './Sidebar';
import { useTestResults } from '../api/hooks';

export default function Layout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('utc-dark-mode');
      if (stored !== null) return stored === 'true';
      return window.matchMedia('(prefers-color-scheme: dark)').matches;
    }
    return false;
  });

  // Persist dark mode preference
  useEffect(() => {
    localStorage.setItem('utc-dark-mode', String(darkMode));
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);

  const toggleDarkMode = useCallback(() => {
    setDarkMode((prev) => !prev);
  }, []);

  const toggleSidebar = useCallback(() => {
    setSidebarCollapsed((prev) => !prev);
  }, []);

  // Test status for sidebar badge
  const { data: testResults } = useTestResults();
  const testStatus =
    testResults != null
      ? testResults.total_failed === 0
        ? 'pass' as const
        : 'fail' as const
      : null;

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={toggleSidebar}
        testStatus={testStatus}
      />

      {/* Main content */}
      <div
        className={clsx(
          'transition-all duration-300',
          sidebarCollapsed ? 'ml-[60px]' : 'ml-[240px]',
        )}
      >
        {/* Top bar */}
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-gray-200 bg-white/80 px-6 backdrop-blur dark:border-gray-700 dark:bg-gray-800/80">
          <h1 className="text-sm font-semibold text-gray-600 dark:text-gray-300">
            Urban Turbulence Corridor
          </h1>

          <div className="flex items-center gap-3">
            <button
              onClick={toggleDarkMode}
              className="rounded-md p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
              aria-label={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {darkMode ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
