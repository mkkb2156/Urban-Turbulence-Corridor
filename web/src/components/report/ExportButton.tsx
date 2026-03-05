import { useState } from 'react';
import { FileJson, FileImage, Loader2 } from 'lucide-react';
import clsx from 'clsx';

interface ExportButtonProps {
  data: Record<string, unknown>;
  reportType: 'area' | 'route' | 'plan';
  title?: string;
  className?: string;
}

export default function ExportButton({ data, reportType, title = 'Flight Mission Report', className }: ExportButtonProps) {
  const [exporting, setExporting] = useState(false);

  const exportJSON = () => {
    const report = {
      title,
      report_type: reportType,
      generated_at: new Date().toISOString(),
      data,
    };
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `utc_report_${reportType}_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const exportScreenshot = async () => {
    setExporting(true);
    try {
      // Find the map canvas
      const canvas = document.querySelector('canvas.maplibregl-canvas') as HTMLCanvasElement;
      if (canvas) {
        const dataUrl = canvas.toDataURL('image/png');
        const a = document.createElement('a');
        a.href = dataUrl;
        a.download = `utc_map_${reportType}_${new Date().toISOString().slice(0, 10)}.png`;
        a.click();
      }
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className={clsx('flex gap-2', className)}>
      <button
        onClick={exportJSON}
        className="flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
      >
        <FileJson size={14} />
        JSON
      </button>
      <button
        onClick={exportScreenshot}
        disabled={exporting}
        className="flex items-center gap-1.5 rounded-md bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600 disabled:opacity-50"
      >
        {exporting ? <Loader2 size={14} className="animate-spin" /> : <FileImage size={14} />}
        Screenshot
      </button>
    </div>
  );
}
