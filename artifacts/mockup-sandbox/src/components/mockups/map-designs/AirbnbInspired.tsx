import React from 'react';
import { Search, SlidersHorizontal, X, ChevronDown } from 'lucide-react';

export function AirbnbInspired() {
  return (
    <div className="relative w-[1280px] h-[800px] overflow-hidden font-sans text-gray-800 bg-blue-50">
      {/* Map Background */}
      <div 
        className="absolute inset-0"
        style={{
          backgroundImage: `
            radial-gradient(ellipse at 40% 50%, #e8e4d8 0%, transparent 50%),
            radial-gradient(circle at 70% 60%, #d8e2cf 0%, transparent 40%),
            radial-gradient(circle at 15% 85%, #d1dcac 0%, transparent 30%),
            radial-gradient(circle at 85% 15%, #dfd3c3 0%, transparent 40%),
            radial-gradient(circle at 50% 20%, #e8e4d8 0%, transparent 60%),
            linear-gradient(135deg, #a7d0e8 0%, #b8dbe9 100%)
          `,
          opacity: 0.85
        }}
      >
        {/* Subtle noise texture */}
        <div 
          className="absolute inset-0 opacity-[0.04] pointer-events-none mix-blend-overlay" 
          style={{ 
            backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=%220 0 200 200%22 xmlns=%22http://www.w3.org/2000/svg%22%3E%3Cfilter id=%22noiseFilter%22%3E%3CfeTurbulence type=%22fractalNoise%22 baseFrequency=%220.8%22 numOctaves=%223%22 stitchTiles=%22stitch%22/%3E%3C/filter%3E%3Crect width=%22100%25%22 height=%22100%25%22 filter=%22url(%23noiseFilter)%22/%3E%3C/svg%3E")' 
          }} 
        />
        
        {/* Map Grid Lines (abstract roads/borders) */}
        <div className="absolute inset-0 opacity-[0.15]"
             style={{
               backgroundImage: `
                 linear-gradient(rgba(255,255,255,0.8) 1px, transparent 1px),
                 linear-gradient(90deg, rgba(255,255,255,0.8) 1px, transparent 1px)
               `,
               backgroundSize: '40px 40px'
             }}
        />

        {/* Marker Clusters */}
        <div className="absolute top-[35%] left-[48%] w-14 h-14 bg-[#FF385C] rounded-full text-white flex items-center justify-center font-bold text-lg shadow-lg border-[3px] border-white z-10 hover:scale-110 transition-transform cursor-pointer">
          4,210
        </div>
        <div className="absolute top-[22%] left-[68%] w-11 h-11 bg-[#FF385C] rounded-full text-white flex items-center justify-center font-bold text-sm shadow-lg border-[3px] border-white z-10 hover:scale-110 transition-transform cursor-pointer">
          842
        </div>
        <div className="absolute top-[65%] left-[78%] w-16 h-16 bg-[#FF385C] rounded-full text-white flex items-center justify-center font-bold text-xl shadow-lg border-[3px] border-white z-10 hover:scale-110 transition-transform cursor-pointer">
          12.5k
        </div>
        <div className="absolute top-[75%] left-[55%] w-12 h-12 bg-[#FF385C] rounded-full text-white flex items-center justify-center font-bold text-md shadow-lg border-[3px] border-white z-10 hover:scale-110 transition-transform cursor-pointer">
          1.2k
        </div>

        {/* Individual Pin / Price Labels */}
        <div className="absolute top-[42%] left-[43%] bg-white text-gray-900 px-3 py-1.5 rounded-full font-extrabold text-sm shadow-md border border-gray-200 hover:scale-105 transition-transform cursor-pointer">
          $125
        </div>
        <div className="absolute top-[38%] left-[53%] bg-white text-gray-900 px-3 py-1.5 rounded-full font-extrabold text-sm shadow-md border border-gray-200 hover:scale-105 transition-transform cursor-pointer">
          $349
        </div>
        {/* Active Pin (Inverted) */}
        <div className="absolute top-[48%] left-[49%] bg-[#FF385C] text-white px-3 py-1.5 rounded-full font-extrabold text-sm shadow-[0_4px_12px_rgba(255,56,92,0.4)] border-2 border-white hover:scale-105 transition-transform cursor-pointer z-20 scale-110">
          $287
        </div>
        <div className="absolute top-[28%] left-[63%] bg-white text-gray-900 px-3 py-1.5 rounded-full font-extrabold text-sm shadow-md border border-gray-200 hover:scale-105 transition-transform cursor-pointer">
          $95
        </div>
        <div className="absolute top-[25%] left-[73%] bg-white text-gray-900 px-3 py-1.5 rounded-full font-extrabold text-sm shadow-md border border-gray-200 hover:scale-105 transition-transform cursor-pointer">
          $150
        </div>
        <div className="absolute top-[60%] left-[72%] bg-white text-gray-900 px-3 py-1.5 rounded-full font-extrabold text-sm shadow-md border border-gray-200 hover:scale-105 transition-transform cursor-pointer">
          $420
        </div>
        <div className="absolute top-[70%] left-[84%] bg-white text-gray-900 px-3 py-1.5 rounded-full font-extrabold text-sm shadow-md border border-gray-200 hover:scale-105 transition-transform cursor-pointer">
          $189
        </div>
      </div>

      {/* Floating Search Bar (Top Center) */}
      <div className="absolute top-8 left-1/2 -translate-x-1/2 z-20 w-[420px]">
        <div className="bg-white rounded-full shadow-[0_6px_20px_rgba(0,0,0,0.08)] border border-gray-200 p-2 flex items-center gap-2 hover:shadow-[0_6px_24px_rgba(0,0,0,0.12)] transition-shadow">
          <div className="bg-gray-100 p-3 rounded-full text-gray-600">
            <Search size={18} strokeWidth={2.5} />
          </div>
          <div className="flex-1 px-3 flex flex-col cursor-pointer">
            <span className="text-sm font-bold text-gray-900 leading-tight">California & Florida</span>
            <span className="text-xs text-gray-500 leading-tight mt-0.5">Any week • Add guests</span>
          </div>
          <div className="w-[1px] h-8 bg-gray-200 mx-1"></div>
          <button className="p-3 rounded-full hover:bg-gray-100 text-gray-700 transition-colors flex items-center justify-center">
            <SlidersHorizontal size={18} strokeWidth={2.5} />
          </button>
        </div>
      </div>

      {/* Floating stats chips (Top Left area, positioned to not overlap with sidebar) */}
      <div className="absolute top-28 left-[340px] z-10 flex gap-2.5">
        <div className="bg-white/95 backdrop-blur-md rounded-full px-3.5 py-1.5 shadow-sm border border-gray-200 text-xs font-bold text-gray-800 flex items-center gap-2 hover:shadow-md transition-shadow cursor-default">
          <span className="w-2 h-2 rounded-full bg-[#FF385C]"></span>
          43,751 LA
        </div>
        <div className="bg-white/95 backdrop-blur-md rounded-full px-3.5 py-1.5 shadow-sm border border-gray-200 text-xs font-bold text-gray-800 flex items-center gap-2 hover:shadow-md transition-shadow cursor-default">
          <span className="w-2 h-2 rounded-full bg-[#FF385C]"></span>
          17,698 Broward
        </div>
        <div className="bg-white/95 backdrop-blur-md rounded-full px-3.5 py-1.5 shadow-sm border border-gray-200 text-xs font-bold text-gray-800 flex items-center gap-2 hover:shadow-md transition-shadow cursor-default">
          <span className="w-2 h-2 rounded-full bg-[#FF385C]"></span>
          13,225 San Diego
        </div>
      </div>

      {/* Sidebar Panel (Left) */}
      <div className="absolute left-0 top-0 bottom-0 w-80 bg-white rounded-r-3xl shadow-[15px_0_40px_rgba(0,0,0,0.12)] z-30 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-[#FF385C] font-bold text-xl tracking-tight">
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-8 h-8">
              <path d="M12.016 1.488c-1.396 0-2.812.39-3.96 1.132L1.734 6.7c-.504.32-.782.88-.734 1.48.046.6.418 1.1 1.018 1.1h1.564v10.518c0 .664.536 1.2 1.2 1.2h4.86c.664 0 1.2-.536 1.2-1.2V14.6h2.316v5.218c0 .664.536 1.2 1.2 1.2h4.86c.664 0 1.2-.536 1.2-1.2V9.28h1.566c.6-.046.972-.546 1.018-1.146.048-.6-.23-1.16-.734-1.48l-6.32-4.08c-1.15-.742-2.566-1.132-3.962-1.132zM12 4.41c.642 0 1.258.18 1.762.5l5.244 3.39H4.996l5.243-3.39c.504-.32 1.12-.5 1.76-.5z" />
            </svg>
            <span className="text-[22px] -mb-1">airbnb</span>
          </div>
          <button className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-500">
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-6 pb-28 custom-scrollbar">
          {/* Badge Area */}
          <div className="mb-7">
            <div className="flex items-center gap-2 mb-1">
              <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#FF385C] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-[#FF385C]"></span>
              </span>
              <h2 className="text-[22px] font-bold text-gray-900 tracking-tight">96,459 listings</h2>
            </div>
            <p className="text-sm text-gray-500 pl-5">Latest snapshot per city</p>
          </div>

          <div className="text-xs font-bold tracking-widest text-gray-400 uppercase mb-4">Filters</div>

          {/* Location Dropdowns */}
          <div className="space-y-4 mb-7">
            <div className="relative group">
              <select className="w-full appearance-none border border-gray-300 rounded-full px-5 py-3.5 text-sm font-semibold text-gray-800 bg-white focus:outline-none focus:border-black focus:ring-1 focus:ring-black hover:border-gray-400 transition-colors cursor-pointer">
                <option>California</option>
                <option>Florida</option>
              </select>
              <ChevronDown size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none group-hover:text-gray-800 transition-colors" />
            </div>
            <div className="relative group">
              <select className="w-full appearance-none border border-gray-300 rounded-full px-5 py-3.5 text-sm font-semibold text-gray-800 bg-white focus:outline-none focus:border-black focus:ring-1 focus:ring-black hover:border-gray-400 transition-colors cursor-pointer">
                <option>All Cities</option>
                <option>Los Angeles</option>
                <option>San Diego</option>
                <option>Miami</option>
              </select>
              <ChevronDown size={18} className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none group-hover:text-gray-800 transition-colors" />
            </div>
          </div>

          <hr className="border-gray-200 my-7" />

          {/* Room Type */}
          <div className="mb-7">
            <h3 className="text-[15px] font-bold text-gray-900 mb-4">Type of place</h3>
            <div className="flex gap-2.5 overflow-x-auto pb-2 -mx-6 px-6 hide-scrollbar">
              <button className="shrink-0 bg-gray-900 text-white px-5 py-2 rounded-full text-sm font-semibold shadow-sm border border-gray-900">All</button>
              <button className="shrink-0 bg-white border border-gray-300 text-gray-700 hover:border-gray-900 hover:text-gray-900 px-5 py-2 rounded-full text-sm font-semibold transition-colors">Entire home</button>
              <button className="shrink-0 bg-white border border-gray-300 text-gray-700 hover:border-gray-900 hover:text-gray-900 px-5 py-2 rounded-full text-sm font-semibold transition-colors">Private room</button>
              <button className="shrink-0 bg-white border border-gray-300 text-gray-700 hover:border-gray-900 hover:text-gray-900 px-5 py-2 rounded-full text-sm font-semibold transition-colors">Hotel</button>
              <button className="shrink-0 bg-white border border-gray-300 text-gray-700 hover:border-gray-900 hover:text-gray-900 px-5 py-2 rounded-full text-sm font-semibold transition-colors">Shared</button>
            </div>
          </div>

          <hr className="border-gray-200 my-7" />

          {/* Price Range Histogram Visual */}
          <div className="mb-7">
            <h3 className="text-[15px] font-bold text-gray-900 mb-6">Price range</h3>
            <div className="px-1">
              <div className="h-14 flex items-end gap-[2px] mb-2">
                {/* Simulated histogram bars */}
                {[1, 3, 6, 12, 18, 28, 40, 50, 42, 30, 22, 15, 8, 5, 3, 2, 1, 1].map((h, i) => (
                  <div key={i} className={`flex-1 rounded-t-sm ${i >= 2 && i <= 14 ? 'bg-gray-800' : 'bg-gray-200'}`} style={{ height: `${h}%` }}></div>
                ))}
              </div>
              
              {/* Slider Track */}
              <div className="relative h-6 mb-8">
                <div className="absolute top-1/2 left-0 right-0 h-[2px] bg-gray-200 -translate-y-1/2"></div>
                <div className="absolute top-1/2 left-[11%] right-[16%] h-[2px] bg-gray-800 -translate-y-1/2"></div>
                
                {/* Thumbs */}
                <div className="absolute top-1/2 left-[11%] w-8 h-8 bg-white border border-gray-300 rounded-full -translate-x-1/2 -translate-y-1/2 shadow-[0_2px_4px_rgba(0,0,0,0.2)] flex items-center justify-center cursor-grab active:cursor-grabbing hover:scale-105 transition-transform">
                  <div className="w-3 flex justify-between">
                    <div className="w-[1px] h-3 bg-gray-400"></div>
                    <div className="w-[1px] h-3 bg-gray-400"></div>
                    <div className="w-[1px] h-3 bg-gray-400"></div>
                  </div>
                </div>
                <div className="absolute top-1/2 left-[84%] w-8 h-8 bg-white border border-gray-300 rounded-full -translate-x-1/2 -translate-y-1/2 shadow-[0_2px_4px_rgba(0,0,0,0.2)] flex items-center justify-center cursor-grab active:cursor-grabbing hover:scale-105 transition-transform">
                  <div className="w-3 flex justify-between">
                    <div className="w-[1px] h-3 bg-gray-400"></div>
                    <div className="w-[1px] h-3 bg-gray-400"></div>
                    <div className="w-[1px] h-3 bg-gray-400"></div>
                  </div>
                </div>
              </div>
              
              {/* Inputs */}
              <div className="flex justify-between items-center text-sm">
                <div className="border border-gray-400 rounded-xl px-4 py-2 w-[45%] flex flex-col focus-within:border-black focus-within:border-2">
                  <span className="text-[11px] text-gray-500 font-normal">Minimum</span>
                  <div className="flex items-center text-gray-900">
                    <span>$</span>
                    <input type="text" defaultValue="50" className="w-full outline-none font-semibold" />
                  </div>
                </div>
                <div className="text-gray-400">-</div>
                <div className="border border-gray-400 rounded-xl px-4 py-2 w-[45%] flex flex-col focus-within:border-black focus-within:border-2">
                  <span className="text-[11px] text-gray-500 font-normal">Maximum</span>
                  <div className="flex items-center text-gray-900">
                    <span>$</span>
                    <input type="text" defaultValue="500+" className="w-full outline-none font-semibold" />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <hr className="border-gray-200 my-7" />

          {/* Toggle Filters */}
          <div className="space-y-7">
            <label className="flex items-start justify-between cursor-pointer group">
              <div className="flex-1 pr-6">
                <span className="text-[15px] font-semibold text-gray-900 block mb-1">Guest favorites</span>
                <span className="text-sm text-gray-500 leading-snug">The most loved homes on Airbnb, according to guests</span>
              </div>
              <div className="relative mt-1">
                <input type="checkbox" className="peer sr-only" />
                <div className="w-12 h-8 bg-gray-300 rounded-full peer-checked:bg-gray-900 transition-colors after:content-[''] after:absolute after:top-1 after:left-1 after:w-6 after:h-6 after:bg-white after:rounded-full after:transition-all peer-checked:after:translate-x-4 border border-transparent peer-hover:border-gray-400"></div>
              </div>
            </label>
            
            <label className="flex items-start justify-between cursor-pointer group">
              <div className="flex-1 pr-6">
                <span className="text-[15px] font-semibold text-gray-900 block mb-1">Instant Book</span>
                <span className="text-sm text-gray-500 leading-snug">Listings you can book without waiting for host approval</span>
              </div>
              <div className="relative mt-1">
                <input type="checkbox" className="peer sr-only" defaultChecked />
                <div className="w-12 h-8 bg-gray-300 rounded-full peer-checked:bg-gray-900 transition-colors after:content-[''] after:absolute after:top-1 after:left-1 after:w-6 after:h-6 after:bg-white after:rounded-full after:transition-all peer-checked:after:translate-x-4 border border-transparent peer-hover:border-gray-400"></div>
              </div>
            </label>
          </div>
        </div>

        {/* Footer Actions (Sticky Bottom) */}
        <div className="absolute bottom-0 left-0 right-0 p-4 px-6 bg-white border-t border-gray-200 z-10 flex items-center justify-between shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
          <button className="text-[15px] font-semibold text-gray-900 underline hover:text-black hover:bg-gray-50 px-2 py-1.5 rounded-lg transition-colors">Clear all</button>
          <button className="bg-[#FF385C] text-white px-7 py-3.5 rounded-xl font-bold text-[15px] hover:bg-[#e03151] transition-colors shadow-sm active:scale-95">
            Show 1,000+ places
          </button>
        </div>
      </div>

      {/* Map Legend (Bottom Right) */}
      <div className="absolute bottom-8 right-8 bg-white/95 backdrop-blur-md rounded-2xl shadow-[0_8px_28px_rgba(0,0,0,0.12)] p-5 w-64 border border-gray-200 z-20">
        <h3 className="text-[15px] font-extrabold text-gray-900 mb-4">Map Legend</h3>
        <div className="space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-4 h-4 rounded-full bg-[#FF385C] border-2 border-white shadow-sm"></div>
              <span className="text-sm font-semibold text-gray-700">Clusters</span>
            </div>
            <span className="text-xs font-bold text-gray-500">96.4k</span>
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-6 h-4 rounded-full bg-white border border-gray-300 shadow-sm"></div>
              <span className="text-sm font-semibold text-gray-700">Listings</span>
            </div>
            <span className="text-xs font-bold text-gray-500">Active</span>
          </div>
          <div className="pt-3 mt-3 border-t border-gray-200">
            <p className="text-[13px] text-gray-500 leading-relaxed font-medium">
              Displaying the most recent snapshot of places to stay in California and Florida.
            </p>
          </div>
        </div>
      </div>

      <style dangerouslySetInnerHTML={{__html: \`
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
        .hide-scrollbar {
          -ms-overflow-style: none;
          scrollbar-width: none;
        }
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background-color: #d1d5db;
          border-radius: 20px;
          border: 2px solid white;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background-color: #9ca3af;
        }
      \`}} />
    </div>
  );
}
