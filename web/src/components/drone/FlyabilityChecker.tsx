import { useState, useCallback, useRef } from 'react';
import { CheckCircle, XCircle, Plane, MapPin, ArrowUp, Upload, List } from 'lucide-react';
import clsx from 'clsx';
import { DRONE_MODELS, HEIGHT_OPTIONS } from '../../api/types';
import type { HeightOption, RiskResponse, BatchRiskResult } from '../../api/types';
import { useFlyabilityCheck, useBatchRiskCheck } from '../../api/hooks';
import { formatWindSpeed, formatCoords } from '../../utils/format';
import { isInTaiwan } from '../../utils/geo';

type TabMode = 'single' | 'batch';

export default function FlyabilityChecker() {
  const [tabMode, setTabMode] = useState<TabMode>('single');
  const [droneId, setDroneId] = useState(DRONE_MODELS[0].id);
  const [lon, setLon] = useState('121.55');
  const [lat, setLat] = useState('25.03');
  const [height, setHeight] = useState<HeightOption>(50);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Batch mode state
  const [batchText, setBatchText] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const flyabilityMutation = useFlyabilityCheck();
  const batchMutation = useBatchRiskCheck();

  const selectedDrone = DRONE_MODELS.find((d) => d.id === droneId);

  const handleCheck = useCallback(() => {
    const lonNum = parseFloat(lon);
    const latNum = parseFloat(lat);

    if (isNaN(lonNum) || isNaN(latNum)) {
      setValidationError('請輸入有效的數值座標。');
      return;
    }

    if (!isInTaiwan(lonNum, latNum)) {
      setValidationError(
        '座標必須在台灣範圍內（經度: 119-123, 緯度: 21-26）。',
      );
      return;
    }

    setValidationError(null);
    flyabilityMutation.mutate({
      lon: lonNum,
      lat: latNum,
      height,
      drone_id: droneId,
    });
  }, [lon, lat, height, droneId, flyabilityMutation]);

  const parseBatchPoints = useCallback(
    (text: string) => {
      const lines = text.trim().split('\n').filter((l) => l.trim() && !l.startsWith('#'));
      const points: { lon: number; lat: number; height?: number; drone_id?: string }[] = [];
      const errors: string[] = [];

      for (let i = 0; i < lines.length; i++) {
        const parts = lines[i].split(',').map((s) => s.trim());
        if (parts.length < 2) {
          errors.push(`第 ${i + 1} 行: 格式錯誤（需要至少 經度,緯度）`);
          continue;
        }
        const lonVal = parseFloat(parts[0]);
        const latVal = parseFloat(parts[1]);
        if (isNaN(lonVal) || isNaN(latVal)) {
          errors.push(`第 ${i + 1} 行: 座標無效`);
          continue;
        }
        if (!isInTaiwan(lonVal, latVal)) {
          errors.push(`第 ${i + 1} 行: 座標不在台灣範圍內`);
          continue;
        }
        points.push({ lon: lonVal, lat: latVal, height, drone_id: droneId });
      }
      return { points, errors };
    },
    [height, droneId],
  );

  const handleBatchCheck = useCallback(() => {
    const { points, errors } = parseBatchPoints(batchText);
    if (errors.length > 0) {
      setValidationError(errors.join('\n'));
      return;
    }
    if (points.length === 0) {
      setValidationError('請輸入至少一個座標點位。');
      return;
    }
    if (points.length > 100) {
      setValidationError('最多支援 100 個點位。');
      return;
    }
    setValidationError(null);
    batchMutation.mutate({ points });
  }, [batchText, parseBatchPoints, batchMutation]);

  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        const text = ev.target?.result as string;
        // Skip header row if it contains non-numeric first field
        const lines = text.split('\n');
        const firstLine = lines[0]?.trim();
        if (firstLine && isNaN(parseFloat(firstLine.split(',')[0]))) {
          setBatchText(lines.slice(1).join('\n'));
        } else {
          setBatchText(text);
        }
      };
      reader.readAsText(file);
      // Reset so same file can be re-uploaded
      e.target.value = '';
    },
    [],
  );

  const result: RiskResponse | undefined = flyabilityMutation.data;
  const flyability = result?.flyability;

  return (
    <div className="card max-w-2xl">
      <h3 className="mb-4 flex items-center gap-2 text-base font-semibold text-gray-800 dark:text-gray-100">
        <Plane size={20} className="text-blue-500" />
        無人機適飛檢查
      </h3>

      {/* Tab switcher */}
      <div className="mb-4 flex rounded-lg bg-gray-100 p-1 dark:bg-gray-700">
        <button
          onClick={() => setTabMode('single')}
          className={clsx(
            'flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
            tabMode === 'single'
              ? 'bg-white text-blue-600 shadow dark:bg-gray-600 dark:text-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
          )}
        >
          <MapPin size={14} /> 單點查詢
        </button>
        <button
          onClick={() => setTabMode('batch')}
          className={clsx(
            'flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors',
            tabMode === 'batch'
              ? 'bg-white text-blue-600 shadow dark:bg-gray-600 dark:text-blue-400'
              : 'text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200',
          )}
        >
          <List size={14} /> 批次查詢
        </button>
      </div>

      {/* Drone selector (shared) */}
      <div className="mb-4">
        <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
          無人機機型
        </label>
        <select
          value={droneId}
          onChange={(e) => setDroneId(e.target.value)}
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        >
          {DRONE_MODELS.map((drone) => (
            <option key={drone.id} value={drone.id}>
              {drone.name} (最大 {drone.max_wind_speed} m/s)
            </option>
          ))}
        </select>
        {selectedDrone && (
          <p className="mt-1 text-xs text-gray-400">
            {selectedDrone.category === 'consumer' ? '消費級' : selectedDrone.category === 'prosumer' ? '專業級' : '企業級'} | {selectedDrone.weight_kg} kg
          </p>
        )}
      </div>

      {/* Height (shared) */}
      <div className="mb-4">
        <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400">
          <ArrowUp size={12} /> 高度 (AGL)
        </label>
        <div className="flex gap-2">
          {HEIGHT_OPTIONS.map((h) => (
            <button
              key={h}
              onClick={() => setHeight(h)}
              className={clsx(
                'rounded-md px-4 py-2 text-sm font-medium transition-colors',
                height === h
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600',
              )}
            >
              {h}m
            </button>
          ))}
        </div>
      </div>

      {/* ─── Single Mode ─── */}
      {tabMode === 'single' && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                <MapPin size={12} /> 經度
              </label>
              <input
                type="number"
                step="0.001"
                min="119"
                max="123"
                value={lon}
                onChange={(e) => setLon(e.target.value)}
                placeholder="121.55"
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              />
            </div>
            <div>
              <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400">
                <MapPin size={12} /> 緯度
              </label>
              <input
                type="number"
                step="0.001"
                min="21"
                max="26"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
                placeholder="25.03"
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              />
            </div>
          </div>

          <button
            onClick={handleCheck}
            disabled={flyabilityMutation.isPending}
            className="btn-primary w-full"
          >
            {flyabilityMutation.isPending ? '檢查中...' : '檢查適飛性'}
          </button>

          {flyabilityMutation.isError && (
            <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              適飛性檢查失敗，請重試。
            </div>
          )}

          {result && flyability && (
            <div
              className={clsx(
                'mt-4 rounded-lg border-2 p-4',
                flyability.flyable
                  ? 'border-risk-green bg-green-50 dark:bg-green-900/20'
                  : 'border-risk-red bg-red-50 dark:bg-red-900/20',
              )}
              data-testid="flyability-result"
            >
              <div className="flex items-center gap-3">
                {flyability.flyable ? (
                  <CheckCircle size={32} className="text-risk-green" />
                ) : (
                  <XCircle size={32} className="text-risk-red" />
                )}
                <div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">
                    {flyability.flyable ? '可飛行' : '不可飛行'}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-300">
                    {flyability.drone_name} 於{' '}
                    {formatCoords(parseFloat(lon), parseFloat(lat))}
                  </p>
                </div>
              </div>

              <div className="mt-3 space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">風速:</span>
                  <span className="font-medium text-gray-800 dark:text-gray-100">
                    {result.wind_speed_50m != null
                      ? formatWindSpeed(result.wind_speed_50m)
                      : 'N/A'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">最大耐受:</span>
                  <span className="font-medium text-gray-800 dark:text-gray-100">
                    {formatWindSpeed(flyability.max_wind_speed)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">餘裕:</span>
                  <span
                    className={clsx(
                      'font-medium',
                      flyability.margin > 0 ? 'text-risk-green' : 'text-risk-red',
                    )}
                  >
                    {flyability.margin > 0 ? '+' : ''}
                    {formatWindSpeed(flyability.margin)}
                  </span>
                </div>
              </div>

              <p className="mt-3 rounded bg-white/60 p-2 text-xs text-gray-600 dark:bg-gray-800/60 dark:text-gray-300">
                {flyability.recommendation}
              </p>
            </div>
          )}
        </>
      )}

      {/* ─── Batch Mode ─── */}
      {tabMode === 'batch' && (
        <>
          <div className="mb-3">
            <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
              座標點位（每行一個: 經度,緯度）
            </label>
            <textarea
              value={batchText}
              onChange={(e) => setBatchText(e.target.value)}
              placeholder={'121.55,25.03\n121.52,25.05\n121.57,25.01'}
              rows={6}
              className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 font-mono text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
            />
            <p className="mt-1 text-xs text-gray-400">
              格式: 經度,緯度（每行一組），最多 100 個點位
            </p>
          </div>

          <div className="mb-4 flex gap-2">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-200 dark:hover:bg-gray-600"
            >
              <Upload size={14} /> 上傳 CSV
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.txt"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={handleBatchCheck}
              disabled={batchMutation.isPending || !batchText.trim()}
              className="btn-primary flex-1"
            >
              {batchMutation.isPending ? '批次檢查中...' : '批次檢查'}
            </button>
          </div>

          {batchMutation.isError && (
            <div className="mt-2 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
              批次查詢失敗，請重試。
            </div>
          )}

          {batchMutation.data && (
            <div className="mt-2">
              {/* Summary */}
              <div className="mb-3 flex gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-700/50">
                <div className="text-center">
                  <div className="text-lg font-bold text-gray-800 dark:text-gray-100">
                    {batchMutation.data.total}
                  </div>
                  <div className="text-xs text-gray-500">總計</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-risk-green">
                    {batchMutation.data.flyable_count}
                  </div>
                  <div className="text-xs text-gray-500">可飛行</div>
                </div>
                <div className="text-center">
                  <div className="text-lg font-bold text-risk-red">
                    {batchMutation.data.not_flyable_count}
                  </div>
                  <div className="text-xs text-gray-500">不可飛行</div>
                </div>
              </div>

              {/* Results table */}
              <div className="max-h-64 overflow-auto rounded-md border border-gray-200 dark:border-gray-600">
                <table className="w-full text-left text-sm">
                  <thead className="sticky top-0 bg-gray-50 text-xs text-gray-600 dark:bg-gray-700 dark:text-gray-300">
                    <tr>
                      <th className="px-3 py-2">#</th>
                      <th className="px-3 py-2">風險</th>
                      <th className="px-3 py-2">風速</th>
                      <th className="px-3 py-2">適飛</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-600">
                    {batchMutation.data.results.map((r: BatchRiskResult, i: number) => (
                      <tr key={i} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                        <td className="px-3 py-1.5 text-gray-500">{i + 1}</td>
                        <td className="px-3 py-1.5">
                          <span
                            className={clsx(
                              'inline-block rounded-full px-2 py-0.5 text-xs font-medium',
                              r.risk_level === 'green' && 'bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300',
                              r.risk_level === 'yellow' && 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/50 dark:text-yellow-300',
                              r.risk_level === 'red' && 'bg-red-100 text-red-700 dark:bg-red-900/50 dark:text-red-300',
                              r.risk_level === 'black' && 'bg-gray-800 text-white dark:bg-gray-900 dark:text-gray-200',
                            )}
                          >
                            {r.risk_label}
                          </span>
                        </td>
                        <td className="px-3 py-1.5 font-mono text-xs">
                          {r.wind_speed_50m != null ? `${r.wind_speed_50m.toFixed(1)} m/s` : 'N/A'}
                        </td>
                        <td className="px-3 py-1.5">
                          {r.flyability ? (
                            r.flyability.flyable ? (
                              <CheckCircle size={16} className="text-risk-green" />
                            ) : (
                              <XCircle size={16} className="text-risk-red" />
                            )
                          ) : (
                            <span className="text-gray-400">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* Validation error */}
      {validationError && (
        <div className="mt-4 whitespace-pre-line rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {validationError}
        </div>
      )}
    </div>
  );
}
