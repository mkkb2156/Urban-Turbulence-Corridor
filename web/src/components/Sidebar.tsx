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
  const mainItems: NavItem[] = [
    { to: '/', icon: LayoutDashboard, label: '儀表板' },
    { to: '/analysis', icon: Navigation, label: '飛行分析' },
    { to: '/corridors', icon: Wind, label: '風廊' },
    { to: '/risk', icon: AlertTriangle, label: '風險評估' },
    { to: '/risk?tab=drone', icon: Plane, label: '無人機檢查' },
  ];

  const advancedItems: NavItem[] = [
    { to: '/fai', icon: BarChart3, label: 'FAI 分析' },
    { to: '/guide', icon: BookOpen, label: '使用指南' },
    { to: '/monitor', icon: Activity, label: '系統監控' },
    {
      to: '/tests',
      icon: FlaskConical,
      label: '測試儀表板',
      badge: testStatus != null && (
        <span
          className={clsx(
            'ml-auto inline-block h-2.5 w-2.5 rounded-full',
            testStatus === 'pass' ? 'bg-risk-green' : 'bg-risk-red',
          )}
          title={testStatus === 'pass' ? '所有測試通過' : '部分測試失敗'}
        />
      ),
    },
  ];

  const renderNavItems = (items: NavItem[]) =>
    items.map((item) => (
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
    ));

  return (
    <aside
      className={clsx(
        'fixed left-0 top-0 z-50 flex h-screen flex-col bg-sidebar text-white transition-all duration-300',
        'max-md:-translate-x-full max-md:w-[240px]',
        mobileOpen && 'max-md:translate-x-0',
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
        {/* Main group */}
        <div className="px-2">
          <p className={clsx('mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-gray-500', collapsed && 'md:hidden')}>
            主要
          </p>
          <ul className="space-y-1">
            {renderNavItems(mainItems)}
          </ul>
        </div>

        {/* Divider */}
        <div className="my-3 border-t border-white/10" />

        {/* Advanced group */}
        <div className="px-2">
          <p className={clsx('mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-gray-500', collapsed && 'md:hidden')}>
            進階
          </p>
          <ul className="space-y-1">
            {renderNavItems(advancedItems)}
          </ul>
        </div>
      </nav>

      {/* Collapse toggle — desktop only */}
      <button
        onClick={onToggle}
        className="hidden h-12 items-center justify-center border-t border-white/10 text-gray-400 hover:text-white md:flex"
        aria-label={collapsed ? '展開側邊欄' : '收合側邊欄'}
      >
        {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
      </button>
    </aside>
  );
}
