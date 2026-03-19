import { X, Eye, EyeOff } from "lucide-react";
import { useUIStore } from "@/store/ui";
import type { MapLayerVisibility } from "@/api/types";

interface LayerItem {
  key: keyof MapLayerVisibility;
  label: string;
  description: string;
}

const LAYERS: LayerItem[] = [
  {
    key: "riskGrid",
    label: "風險網格",
    description: "100m 網格風險色碼（綠/黃/紅/黑）",
  },
  {
    key: "corridors",
    label: "風廊",
    description: "台北 10 條主要通風廊道",
  },
  {
    key: "windField",
    label: "風場粒子",
    description: "WebGL GPU 風場動畫（100K 粒子）",
  },
  {
    key: "airspace",
    label: "空域限制",
    description: "禁飛區 / 限制空域",
  },
  {
    key: "buildings3d",
    label: "3D 建築",
    description: "建築物立體模型（zoom 14+ 顯示）",
  },
  {
    key: "morphology",
    label: "形態學",
    description: "FAI / LCZ / 地表粗糙度",
  },
];

export function LayerDrawer() {
  const { layerDrawerOpen, setLayerDrawerOpen, layers, toggleLayer } =
    useUIStore();

  if (!layerDrawerOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="absolute inset-0 z-30 bg-black/30"
        onClick={() => setLayerDrawerOpen(false)}
      />

      {/* Drawer */}
      <div className="absolute top-14 right-0 bottom-12 z-40 w-80 bg-gray-900/95 backdrop-blur-sm border-l border-gray-700/50 overflow-y-auto">
        <div className="flex items-center justify-between p-4 border-b border-gray-700/50">
          <h2 className="text-lg font-semibold text-white">圖層控制</h2>
          <button
            onClick={() => setLayerDrawerOpen(false)}
            className="rounded-lg p-1 text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-4 space-y-2">
          {LAYERS.map((item) => {
            const visible = layers[item.key];
            return (
              <button
                key={item.key}
                onClick={() => toggleLayer(item.key)}
                className={`w-full flex items-center gap-3 rounded-lg p-3 text-left transition-colors ${
                  visible
                    ? "bg-blue-900/30 border border-blue-500/30"
                    : "bg-gray-800/50 border border-gray-700/30 hover:bg-gray-800"
                }`}
              >
                {visible ? (
                  <Eye className="h-5 w-5 text-blue-400 shrink-0" />
                ) : (
                  <EyeOff className="h-5 w-5 text-gray-500 shrink-0" />
                )}
                <div>
                  <div
                    className={`text-sm font-medium ${visible ? "text-white" : "text-gray-400"}`}
                  >
                    {item.label}
                  </div>
                  <div className="text-xs text-gray-500">{item.description}</div>
                </div>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}
