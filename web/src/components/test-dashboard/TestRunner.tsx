import { Play, Loader2 } from 'lucide-react';
import { useTriggerTests } from '../../api/hooks';

export default function TestRunner() {
  const triggerMutation = useTriggerTests();

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => triggerMutation.mutate()}
        disabled={triggerMutation.isPending}
        className="btn-primary flex items-center gap-2"
      >
        {triggerMutation.isPending ? (
          <>
            <Loader2 size={16} className="animate-spin" />
            測試執行中...
          </>
        ) : (
          <>
            <Play size={16} />
            執行所有測試
          </>
        )}
      </button>

      {triggerMutation.isSuccess && (
        <span className="text-xs text-green-600 dark:text-green-400">
          測試已成功觸發
        </span>
      )}

      {triggerMutation.isError && (
        <span className="text-xs text-red-600 dark:text-red-400">
          觸發測試失敗
        </span>
      )}
    </div>
  );
}
