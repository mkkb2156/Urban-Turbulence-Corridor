import { useState, useCallback } from 'react';
import { CheckCircle, XCircle, Plane, MapPin, ArrowUp } from 'lucide-react';
import clsx from 'clsx';
import { DRONE_MODELS, HEIGHT_OPTIONS } from '../../api/types';
import type { HeightOption, RiskResponse } from '../../api/types';
import { useFlyabilityCheck } from '../../api/hooks';
import { formatWindSpeed, formatCoords } from '../../utils/format';
import { isInTaiwan } from '../../utils/geo';

export default function FlyabilityChecker() {
  const [droneId, setDroneId] = useState(DRONE_MODELS[0].id);
  const [lon, setLon] = useState('121.55');
  const [lat, setLat] = useState('25.03');
  const [height, setHeight] = useState<HeightOption>(50);
  const [validationError, setValidationError] = useState<string | null>(null);

  const flyabilityMutation = useFlyabilityCheck();

  const selectedDrone = DRONE_MODELS.find((d) => d.id === droneId);

  const handleCheck = useCallback(() => {
    const lonNum = parseFloat(lon);
    const latNum = parseFloat(lat);

    if (isNaN(lonNum) || isNaN(latNum)) {
      setValidationError('Please enter valid numeric coordinates.');
      return;
    }

    if (!isInTaiwan(lonNum, latNum)) {
      setValidationError(
        'Coordinates must be within Taiwan (lon: 119-123, lat: 21-26).',
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

  const result: RiskResponse | undefined = flyabilityMutation.data;
  const flyability = result?.flyability;

  return (
    <div className="card max-w-lg">
      <h3 className="mb-4 flex items-center gap-2 text-base font-semibold text-gray-800 dark:text-gray-100">
        <Plane size={20} className="text-blue-500" />
        Drone Flyability Checker
      </h3>

      {/* Drone selector */}
      <div className="mb-4">
        <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
          Drone Model
        </label>
        <select
          value={droneId}
          onChange={(e) => setDroneId(e.target.value)}
          className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
        >
          {DRONE_MODELS.map((drone) => (
            <option key={drone.id} value={drone.id}>
              {drone.name} (max {drone.max_wind_speed} m/s)
            </option>
          ))}
        </select>
        {selectedDrone && (
          <p className="mt-1 text-xs text-gray-400">
            {selectedDrone.category} | {selectedDrone.weight_kg} kg
          </p>
        )}
      </div>

      {/* Coordinates */}
      <div className="mb-4 grid grid-cols-2 gap-3">
        <div>
          <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400">
            <MapPin size={12} /> Longitude
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
            <MapPin size={12} /> Latitude
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

      {/* Height */}
      <div className="mb-4">
        <label className="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-gray-400">
          <ArrowUp size={12} /> Height (AGL)
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

      {/* Validation error */}
      {validationError && (
        <div className="mb-4 rounded-md bg-red-50 p-2 text-xs text-red-700 dark:bg-red-900/30 dark:text-red-300">
          {validationError}
        </div>
      )}

      {/* Check button */}
      <button
        onClick={handleCheck}
        disabled={flyabilityMutation.isPending}
        className="btn-primary w-full"
      >
        {flyabilityMutation.isPending ? 'Checking...' : 'Check Flyability'}
      </button>

      {/* Error */}
      {flyabilityMutation.isError && (
        <div className="mt-4 rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/30 dark:text-red-300">
          Failed to check flyability. Please try again.
        </div>
      )}

      {/* Result */}
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
                {flyability.flyable ? 'Flyable' : 'Not Flyable'}
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                {flyability.drone_name} at{' '}
                {formatCoords(parseFloat(lon), parseFloat(lat))}
              </p>
            </div>
          </div>

          <div className="mt-3 space-y-1 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">
                Wind Speed:
              </span>
              <span className="font-medium text-gray-800 dark:text-gray-100">
                {result.wind_speed_50m != null
                  ? formatWindSpeed(result.wind_speed_50m)
                  : 'N/A'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">
                Max Tolerance:
              </span>
              <span className="font-medium text-gray-800 dark:text-gray-100">
                {formatWindSpeed(flyability.max_wind_speed)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-500 dark:text-gray-400">
                Margin:
              </span>
              <span
                className={clsx(
                  'font-medium',
                  flyability.margin > 0
                    ? 'text-risk-green'
                    : 'text-risk-red',
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
    </div>
  );
}
