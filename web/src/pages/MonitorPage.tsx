import { Activity, RefreshCw, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { useMonitor } from '../api/hooks';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../api/hooks';
import type { MonitorService } from '../api/types';
import clsx from 'clsx';

function StatusIcon({ status }: { status: string }) {
  if (status === 'healthy') return <CheckCircle2 size={28} className="text-green-500" />;
  if (status === 'degraded') return <AlertTriangle size={28} className="text-yellow-500" />;
  return <XCircle size={28} className="text-red-500" />;
}

function StatusBadge({ status }: { status: 'up' | 'down' }) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold',
        status === 'up'
          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
          : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
      )}
    >
      <span
        className={clsx(
          'h-2 w-2 rounded-full',
          status === 'up' ? 'bg-green-500' : 'bg-red-500',
        )}
      />
      {status === 'up' ? '在線' : '離線'}
    </span>
  );
}

function ServiceCard({ service }: { service: MonitorService }) {
  return (
    <div className="card flex items-start justify-between gap-4">
      <div className="flex-1">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-gray-900 dark:text-white">{service.name}</h3>
          <StatusBadge status={service.status} />
        </div>

        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          延遲: <span className="font-mono">{service.latency_ms.toFixed(0)}ms</span>
        </p>

        {service.error && (
          <p className="mt-2 rounded bg-red-50 px-3 py-1.5 text-xs text-red-700 dark:bg-red-900/20 dark:text-red-400">
            {service.error}
          </p>
        )}

        {Object.keys(service.details).length > 0 && (
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-gray-500 dark:text-gray-400">
            {Object.entries(service.details).map(([key, value]) => (
              <span key={key} className="rounded bg-gray-100 px-2 py-0.5 dark:bg-gray-700">
                {key}: <span className="font-mono font-semibold">{String(value)}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function MonitorPage() {
  const { data, isLoading, isFetching, dataUpdatedAt } = useMonitor();
  const queryClient = useQueryClient();

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.monitor() });
  };

  const lastChecked = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : '—';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-xl font-bold text-gray-900 dark:text-white">
            <Activity size={24} className="text-blue-500" />
            系統監控
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            所有外部服務與依賴項目的即時健康檢查
          </p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isFetching}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
        >
          <RefreshCw size={16} className={isFetching ? 'animate-spin' : ''} />
          重新整理
        </button>
      </div>

      {/* Overall Status */}
      {isLoading ? (
        <div className="card animate-pulse">
          <div className="h-8 w-48 rounded bg-gray-200 dark:bg-gray-700" />
        </div>
      ) : data ? (
        <div
          className={clsx(
            'card flex items-center gap-4 border-l-4',
            data.status === 'healthy' && 'border-l-green-500',
            data.status === 'degraded' && 'border-l-yellow-500',
            data.status === 'unhealthy' && 'border-l-red-500',
          )}
        >
          <StatusIcon status={data.status} />
          <div>
            <p className="text-lg font-bold capitalize text-gray-900 dark:text-white">
              {data.status === 'healthy'
                ? '所有系統正常運作'
                : data.status === 'degraded'
                  ? '部分服務中斷'
                  : '主要服務中斷'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              上次檢查: {lastChecked} &middot; 版本: {data.version} &middot; 自動更新: 30 秒
            </p>
          </div>
        </div>
      ) : (
        <div className="card text-center text-sm text-gray-500">
          無法取得監控狀態。
        </div>
      )}

      {/* Service List */}
      <div>
        <h3 className="mb-3 text-sm font-semibold text-gray-700 dark:text-gray-200">
          服務 ({data?.services.filter((s) => s.status === 'up').length ?? 0}/
          {data?.services.length ?? 0} 在線)
        </h3>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="card animate-pulse">
                <div className="h-5 w-40 rounded bg-gray-200 dark:bg-gray-700" />
                <div className="mt-2 h-3 w-24 rounded bg-gray-200 dark:bg-gray-700" />
              </div>
            ))}
          </div>
        ) : data ? (
          <div className="space-y-3">
            {data.services.map((service) => (
              <ServiceCard key={service.name} service={service} />
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
