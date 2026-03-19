import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { UTCMap } from "@/map/UTCMap";
import { Toolbar } from "@/map/controls/Toolbar";
import { TimeSlider } from "@/map/controls/TimeSlider";
import { LayerDrawer } from "@/map/controls/LayerDrawer";
import { FlightPanel } from "@/panels/FlightPanel";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="relative h-screen w-screen overflow-hidden bg-gray-900">
        {/* 頂部工具列 */}
        <Toolbar />

        {/* 主地圖 */}
        <div className="absolute inset-0 top-14">
          <UTCMap />
        </div>

        {/* 右側結論面板 */}
        <FlightPanel />

        {/* 底部時間軸 */}
        <TimeSlider />

        {/* 圖層控制抽屜 */}
        <LayerDrawer />
      </div>
    </QueryClientProvider>
  );
}
