import { Plane, ChevronDown } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import clsx from 'clsx';
import { DRONE_MODELS } from '../../api/types';
import type { DroneModel } from '../../api/types';

interface DroneSelectorProps {
  selected: DroneModel | null;
  onSelect: (drone: DroneModel | null) => void;
  compact?: boolean;
}

export default function DroneSelector({ selected, onSelect, compact }: DroneSelectorProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const categoryColors: Record<string, string> = {
    consumer: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    prosumer: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    enterprise: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
  };

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={clsx(
          'flex items-center gap-2 rounded-md bg-white shadow-md hover:bg-gray-50 dark:bg-gray-800 dark:hover:bg-gray-700',
          compact ? 'px-2 py-1.5' : 'px-3 py-2',
        )}
      >
        <Plane size={compact ? 14 : 16} className="text-blue-500" />
        <span className={clsx('font-medium text-gray-700 dark:text-gray-200', compact ? 'text-xs' : 'text-sm')}>
          {selected ? selected.name : '選擇無人機'}
        </span>
        <ChevronDown size={14} className={clsx('text-gray-400 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute left-0 top-full z-50 mt-1 w-full min-w-[256px] rounded-md bg-white shadow-lg dark:bg-gray-800 max-md:right-0">
          <div className="p-1">
            <button
              onClick={() => { onSelect(null); setOpen(false); }}
              className={clsx(
                'flex w-full items-center rounded px-3 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700',
                !selected && 'bg-blue-50 dark:bg-blue-900/30',
              )}
            >
              <span className="text-gray-500">未選擇無人機</span>
            </button>
            {DRONE_MODELS.map((drone) => (
              <button
                key={drone.id}
                onClick={() => { onSelect(drone); setOpen(false); }}
                className={clsx(
                  'flex w-full items-center justify-between rounded px-3 py-2.5 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 md:py-2',
                  selected?.id === drone.id && 'bg-blue-50 dark:bg-blue-900/30',
                )}
              >
                <div>
                  <div className="font-medium text-gray-800 dark:text-gray-200">{drone.name}</div>
                  <div className="text-xs text-gray-500">
                    最大 {drone.max_wind_speed} m/s &middot; {drone.weight_kg} kg
                  </div>
                </div>
                <span className={clsx('rounded-full px-2 py-0.5 text-xs font-medium', categoryColors[drone.category] || categoryColors.consumer)}>
                  {drone.category === 'consumer' ? '消費級' : drone.category === 'prosumer' ? '專業級' : '企業級'}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
