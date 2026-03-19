import { useState, useCallback } from "react";
import { Search, Layers, Wind } from "lucide-react";
import { useMapStore } from "@/store/map";
import { useFlightStore } from "@/store/flight";
import { useUIStore } from "@/store/ui";
import { DRONE_MODELS } from "@/api/types";

export function Toolbar() {
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const flyTo = useMapStore((s) => s.flyTo);
  const setSelectedPoint = useMapStore((s) => s.setSelectedPoint);
  const { selectedDrone, setDrone } = useFlightStore();
  const { setLayerDrawerOpen, setFlightPanelOpen } = useUIStore();

  const handleSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!searchQuery.trim()) return;

      setSearching(true);
      try {
        // Nominatim geocoding (Taiwan-biased)
        const res = await fetch(
          `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&countrycodes=tw&limit=1`,
        );
        const data = await res.json();
        if (data.length > 0) {
          const { lon, lat } = data[0];
          const lng = parseFloat(lon);
          const latNum = parseFloat(lat);
          flyTo(lng, latNum, 15);
          setSelectedPoint({ lng, lat: latNum });
          setFlightPanelOpen(true);
        }
      } catch (err) {
        console.error("Geocoding failed:", err);
      } finally {
        setSearching(false);
      }
    },
    [searchQuery, flyTo, setSelectedPoint, setFlightPanelOpen],
  );

  return (
    <div className="absolute top-0 left-0 right-0 z-20 flex h-14 items-center gap-3 bg-gray-900/90 px-4 backdrop-blur-sm border-b border-gray-700/50">
      {/* Logo */}
      <div className="flex items-center gap-2 mr-2">
        <Wind className="h-6 w-6 text-blue-400" />
        <span className="text-lg font-bold text-white tracking-tight">UTC</span>
        <span className="text-xs text-gray-400 hidden sm:inline">v4</span>
      </div>

      {/* 搜尋 */}
      <form onSubmit={handleSearch} className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜尋地點..."
          disabled={searching}
          className="w-full rounded-lg bg-gray-800 border border-gray-600 py-2 pl-9 pr-4 text-sm text-white placeholder-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </form>

      {/* 機型選擇 */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-400 hidden md:inline">機型</span>
        <select
          value={selectedDrone.id}
          onChange={(e) => setDrone(e.target.value)}
          className="rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-sm text-white focus:border-blue-500 focus:outline-none"
        >
          {DRONE_MODELS.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>

      {/* 圖層 */}
      <button
        onClick={() => setLayerDrawerOpen(true)}
        className="flex items-center gap-1 rounded-lg bg-gray-800 border border-gray-600 px-3 py-2 text-sm text-white hover:bg-gray-700 transition-colors"
      >
        <Layers className="h-4 w-4" />
        <span className="hidden sm:inline">圖層</span>
      </button>
    </div>
  );
}
