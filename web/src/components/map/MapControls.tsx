import { Layers, ChevronDown } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import clsx from 'clsx';
import type { MapLayers, HeightOption } from '../../api/types';
import { HEIGHT_OPTIONS } from '../../api/types';
import { formatHeight } from '../../utils/format';

interface MapControlsProps {
  height: HeightOption;
  onHeightChange: (h: HeightOption) => void;
  layers: MapLayers;
  onLayersChange: (layers: MapLayers) => void;
}

export default function MapControls({
  height,
  onHeightChange,
  layers,
  onLayersChange,
}: MapControlsProps) {
  const [layerPanelOpen, setLayerPanelOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  // Close panel on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setLayerPanelOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const toggleLayer = (key: keyof MapLayers) => {
    onLayersChange({ ...layers, [key]: !layers[key] });
  };

  const layerOptions: { key: keyof MapLayers; label: string }[] = [
    { key: 'risk', label: '風險網格' },
    { key: 'fai', label: 'FAI 圖層' },
    { key: 'corridors', label: '風廊' },
    { key: 'wind_arrows', label: '風箭頭' },
    { key: 'particles', label: '風場動畫' },
  ];

  return (
    <div className="flex flex-col gap-2" ref={panelRef}>
      {/* Height selector */}
      <div className="rounded-md bg-white shadow-md dark:bg-gray-800">
        <div className="px-3 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
          高度
        </div>
        <div className="flex gap-1 px-2 pb-2">
          {HEIGHT_OPTIONS.map((h) => (
            <button
              key={h}
              onClick={() => onHeightChange(h)}
              className={clsx(
                'rounded px-2.5 py-1 text-xs font-medium transition-colors',
                height === h
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600',
              )}
            >
              {formatHeight(h)}
            </button>
          ))}
        </div>
      </div>

      {/* Layer toggles */}
      <div className="relative">
        <button
          onClick={() => setLayerPanelOpen(!layerPanelOpen)}
          className="flex items-center gap-2 rounded-md bg-white px-3 py-2 shadow-md hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700"
        >
          <Layers size={16} className="text-gray-600 dark:text-gray-300" />
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
            圖層
          </span>
          <ChevronDown
            size={14}
            className={clsx(
              'text-gray-400 transition-transform',
              layerPanelOpen && 'rotate-180',
            )}
          />
        </button>

        {layerPanelOpen && (
          <div className="absolute left-0 top-full mt-1 w-48 rounded-md bg-white p-2 shadow-lg dark:bg-gray-800">
            {layerOptions.map(({ key, label }) => (
              <label
                key={key}
                className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-gray-50 dark:hover:bg-gray-700"
              >
                <input
                  type="checkbox"
                  checked={layers[key]}
                  onChange={() => toggleLayer(key)}
                  className="h-3.5 w-3.5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-gray-700 dark:text-gray-200">{label}</span>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
