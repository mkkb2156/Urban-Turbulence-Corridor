import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Wind,
  AlertTriangle,
  BarChart3,
  Plane,
  FlaskConical,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import clsx from 'clsx';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  testStatus?: 'pass' | 'fail' | null;
}

interface NavItem {
  to: string;
  icon: React.ComponentType<{ size?: number }>;
  label: string;
  badge?: React.ReactNode;
}

export default function Sidebar({ collapsed, onToggle, testStatus }: SidebarProps) {
  const navItems: NavItem[] = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/corridors', icon: Wind, label: 'Wind Corridors' },
    { to: '/risk', icon: AlertTriangle, label: 'Risk Assessment' },
    { to: '/fai', icon: BarChart3, label: 'FAI Analysis' },
    { to: '/risk?tab=drone', icon: Plane, label: 'Drone Check' },
    {
      to: '/tests',
      icon: FlaskConical,
      label: 'Test Dashboard',
      badge: testStatus != null && (
        <span
          className={clsx(
            'ml-auto inline-block h-2.5 w-2.5 rounded-full',
            testStatus === 'pass' ? 'bg-risk-green' : 'bg-risk-red',
          )}
          title={testStatus === 'pass' ? 'All tests passing' : 'Some tests failing'}
        />
      ),
    },
  ];

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 z-30 flex h-screen flex-col bg-sidebar text-white transition-all duration-300',
        collapsed ? 'w-sidebar-collapsed' : 'w-sidebar',
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-white/10 px-4">
        <Wind size={24} className="shrink-0 text-sky-400" />
        {!collapsed && (
          <span className="ml-3 text-lg font-bold tracking-tight">UTC</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-sidebar-active text-white'
                      : 'text-gray-300 hover:bg-sidebar-hover hover:text-white',
                    collapsed && 'justify-center',
                  )
                }
                title={collapsed ? item.label : undefined}
              >
                <item.icon size={20} />
                {!collapsed && (
                  <>
                    <span className="ml-3">{item.label}</span>
                    {item.badge}
                  </>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="flex h-12 items-center justify-center border-t border-white/10 text-gray-400 hover:text-white"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </aside>
  );
}
