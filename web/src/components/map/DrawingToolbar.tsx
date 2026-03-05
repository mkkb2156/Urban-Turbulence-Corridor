import { Pentagon, Route, MapPin, Trash2, Undo2 } from 'lucide-react';
import clsx from 'clsx';

export type DrawMode = 'none' | 'polygon' | 'route' | 'point';

interface DrawingToolbarProps {
  mode: DrawMode;
  onModeChange: (mode: DrawMode) => void;
  onClear: () => void;
  onUndo: () => void;
  hasDrawing: boolean;
  className?: string;
}

export default function DrawingToolbar({
  mode,
  onModeChange,
  onClear,
  onUndo,
  hasDrawing,
  className,
}: DrawingToolbarProps) {
  const tools: { id: DrawMode; icon: typeof Pentagon; label: string; description: string }[] = [
    { id: 'polygon', icon: Pentagon, label: 'Area', description: 'Draw polygon to analyze area' },
    { id: 'route', icon: Route, label: 'Route', description: 'Draw route for wind analysis' },
    { id: 'point', icon: MapPin, label: 'Point', description: 'Drop pins for start/end' },
  ];

  return (
    <div className={clsx('flex flex-col gap-1 rounded-md bg-white p-1.5 shadow-md dark:bg-gray-800', className)}>
      <div className="px-1.5 py-1 text-xs font-medium text-gray-400">Draw</div>
      {tools.map(({ id, icon: Icon, label, description }) => (
        <button
          key={id}
          onClick={() => onModeChange(mode === id ? 'none' : id)}
          className={clsx(
            'flex items-center gap-2 rounded px-2 py-1.5 text-xs transition-colors',
            mode === id
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700',
          )}
          title={description}
        >
          <Icon size={14} />
          <span>{label}</span>
        </button>
      ))}

      {hasDrawing && (
        <>
          <div className="my-1 border-t border-gray-200 dark:border-gray-600" />
          <button
            onClick={onUndo}
            className="flex items-center gap-2 rounded px-2 py-1.5 text-xs text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-700"
          >
            <Undo2 size={14} />
            <span>Undo</span>
          </button>
          <button
            onClick={onClear}
            className="flex items-center gap-2 rounded px-2 py-1.5 text-xs text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-900/20"
          >
            <Trash2 size={14} />
            <span>Clear</span>
          </button>
        </>
      )}
    </div>
  );
}
