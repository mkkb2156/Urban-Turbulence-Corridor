import { NavLink } from 'react-router-dom';
import type { LucideIcon } from 'lucide-react';
import {
  LayoutDashboard,
  Wind,
  AlertTriangle,
  BarChart3,
  Plane,
  FlaskConical,
  Navigation,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  Activity,
} from 'lucide-react';
import clsx from 'clsx';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  testStatus?: 'pass' | 'fail' | null;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

interface NavItem {
  to: string;
  icon: LucideIcon;
  label: string;
  badge?: React.ReactNode;
}

export default function Sidebar({ collapsed, onToggle, testStatus, mobileOpen, onMobileClose }: SidebarProps) {
  const navItems: NavItem[] = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/analysis', icon: Navigation, label: 'Flight Analysis' },
    { to: '/corridors', icon: Wind, label: 'Wind Corridors' },
    { to: '/risk', icon: AlertTriangle, label: 'Risk Assessment' },
    { to: '/fai', icon: BarChart3, label: 'FAI Analysis' },
    { to: '/risk?tab=drone', icon: Plane, label: 'Drone Check' },
    { to: '/guide', icon: BookOpen, label: 'How to Use' },
    { to: '/monitor', icon: Activity, label: 'Monitor' },
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
        'fixed left-0 top-0 z-50 flex h-screen flex-col bg-sidebar text-white transition-all duration-300',
        // Mobile: slide in/out as overlay
        'max-md:-translate-x-full max-md:w-[240px]',
        mobileOpen && 'max-md:translate-x-0',
        // Desktop: static sidebar with collapse
        'md:z-30',
        collapsed ? 'md:w-sidebar-collapsed' : 'md:w-sidebar',
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center border-b border-white/10 px-4">
        <Wind size={24} className="shrink-0 text-sky-400" />
        <span className={clsx('ml-3 text-lg font-bold tracking-tight', collapsed && 'md:hidden')}>
          UTC
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto py-4">
        <ul className="space-y-1 px-2">
          {navItems.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                onClick={onMobileClose}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center rounded-md px-3 py-2.5 text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-sidebar-active text-white'
                      : 'text-gray-300 hover:bg-sidebar-hover hover:text-white',
                    collapsed && 'md:justify-center',
                  )
                }
                title={collapsed ? item.label : undefined}
              >
                <item.icon size={20} />
                {/* Always show label on mobile; hide on desktop when collapsed */}
                <span className={clsx('ml-3', collapsed && 'md:hidden')}>
                  {item.label}
                </span>
                {item.badge && (
                  <span className={clsx(collapsed && 'md:hidden')}>
                    {item.badge}
                  </span>
                )}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* Collapse toggle — desktop only */}
      <button
        onClick={onToggle}
        className="hidden h-12 items-center justify-center border-t border-white/10 text-gray-400 hover:text-white md:flex"
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </aside>
  );
}
