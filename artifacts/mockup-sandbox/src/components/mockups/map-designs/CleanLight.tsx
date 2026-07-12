import React from 'react';

export function CleanLight() {
  return (
    <div className="w-[1280px] h-[800px] flex overflow-hidden font-sans text-slate-800 bg-white">
      {/* Sidebar */}
      <div className="w-[320px] flex-shrink-0 bg-white border-r border-slate-200 flex flex-col relative z-10 shadow-[2px_0_15px_-5px_rgba(0,0,0,0.05)]">
        
        {/* Header */}
        <div className="p-6 pb-5 border-b border-slate-100">
          <a href="#" className="text-xs font-semibold text-[#4f46e5] hover:text-indigo-700 mb-3 inline-flex items-center">
            &larr; Revenue Estimator
          </a>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 mb-1">Airbnb Map</h1>
          <p className="text-sm text-slate-500">Explore California &amp; Florida</p>
        </div>

        {/* Filters */}
        <div className="p-6 flex-1 overflow-y-auto">
          <div className="mb-5">
            <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Filters</h2>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">State</label>
              <select className="w-full bg-slate-50 border border-slate-200 text-sm rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 focus:border-[#4f46e5] appearance-none bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20width%3D%2220%22%20height%3D%2220%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M5%208l5%205%205-5%22%20stroke%3D%22%2394a3b8%22%20stroke-width%3D%222%22%20fill%3D%22none%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3C%2Fsvg%3E')] bg-[length:20px_20px] bg-[position:right_8px_center] bg-no-repeat text-slate-700 cursor-pointer">
                <option>California</option>
                <option>Florida</option>
              </select>
            </div>
            
            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">City / Region</label>
              <select className="w-full bg-slate-50 border border-slate-200 text-sm rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 focus:border-[#4f46e5] appearance-none bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20width%3D%2220%22%20height%3D%2220%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M5%208l5%205%205-5%22%20stroke%3D%22%2394a3b8%22%20stroke-width%3D%222%22%20fill%3D%22none%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3C%2Fsvg%3E')] bg-[length:20px_20px] bg-[position:right_8px_center] bg-no-repeat text-slate-400 cursor-pointer">
                <option>All cities</option>
                <option>Los Angeles</option>
                <option>San Francisco</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Room Type</label>
              <select className="w-full bg-slate-50 border border-slate-200 text-sm rounded-lg px-3 py-2 pr-8 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 focus:border-[#4f46e5] appearance-none bg-[url('data:image/svg+xml;charset=US-ASCII,%3Csvg%20width%3D%2220%22%20height%3D%2220%22%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%3E%3Cpath%20d%3D%22M5%208l5%205%205-5%22%20stroke%3D%22%2394a3b8%22%20stroke-width%3D%222%22%20fill%3D%22none%22%20stroke-linecap%3D%22round%22%20stroke-linejoin%3D%22round%22%2F%3E%3C%2Fsvg%3E')] bg-[length:20px_20px] bg-[position:right_8px_center] bg-no-repeat text-slate-400 cursor-pointer">
                <option>All types</option>
                <option>Entire home/apt</option>
                <option>Private room</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-600 mb-1.5">Price Range ($)</label>
              <div className="flex items-center space-x-2">
                <input type="number" placeholder="Min" className="w-full bg-slate-50 border border-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 focus:border-[#4f46e5] placeholder-slate-400" />
                <span className="text-slate-400">-</span>
                <input type="number" placeholder="Max" className="w-full bg-slate-50 border border-slate-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-[#4f46e5]/50 focus:border-[#4f46e5] placeholder-slate-400" />
              </div>
            </div>

            <div className="pt-3">
              <button className="w-full bg-[#4f46e5] hover:bg-indigo-700 text-white font-medium text-sm rounded-lg px-4 py-2.5 transition-colors shadow-sm shadow-indigo-600/20">
                Apply Filters
              </button>
              <div className="text-center mt-3">
                <button className="text-sm text-slate-400 hover:text-slate-600 transition-colors">
                  Reset
                </button>
              </div>
            </div>
          </div>

          {/* Stats Section */}
          <div className="bg-slate-50 rounded-xl p-4 mt-4 border border-slate-100/60 shadow-sm">
            <h3 className="text-2xl font-bold text-slate-900 mb-0.5">1,000</h3>
            <p className="text-xs text-slate-500 mb-3 font-medium">listings shown</p>
            
            <div className="flex flex-wrap gap-2">
              <div className="inline-flex items-center px-2 py-1 bg-white border border-slate-200 rounded-full text-[10px] font-medium text-slate-600 shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-[#4f46e5] mr-1.5"></span>
                Entire home/apt (654)
              </div>
              <div className="inline-flex items-center px-2 py-1 bg-white border border-slate-200 rounded-full text-[10px] font-medium text-slate-600 shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5"></span>
                Private room (312)
              </div>
              <div className="inline-flex items-center px-2 py-1 bg-white border border-slate-200 rounded-full text-[10px] font-medium text-slate-600 shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5"></span>
                Hotel room (24)
              </div>
              <div className="inline-flex items-center px-2 py-1 bg-white border border-slate-200 rounded-full text-[10px] font-medium text-slate-600 shadow-sm">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 mr-1.5"></span>
                Shared room (10)
              </div>
            </div>
          </div>
        </div>

        {/* About / Footer */}
        <div className="p-6 pt-4 mt-auto border-t border-slate-100">
          <div className="text-xs text-slate-400 leading-relaxed">
            <p>Data: InsideAirbnb &middot; CC BY 4.0</p>
            <p>Latest snapshot: Sep 2023</p>
          </div>
        </div>
      </div>

      {/* Map Area */}
      <div className="flex-1 relative bg-[#f5f0eb] overflow-hidden">
        {/* Abstract Map Background */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" xmlns="http://www.w3.org/2000/svg">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#e8e2dc" strokeWidth="0.5"/>
            </pattern>
            <pattern id="grid-large" width="160" height="160" patternUnits="userSpaceOnUse">
              <rect width="160" height="160" fill="url(#grid)" />
              <path d="M 160 0 L 0 0 0 160" fill="none" stroke="#dcd3cc" strokeWidth="1"/>
            </pattern>
          </defs>
          
          {/* Water */}
          <path d="M 0,0 L 400,0 C 450,150 250,250 300,450 C 350,650 150,750 0,800 Z" fill="#dbeafe" opacity="0.8" />
          <path d="M 960,800 L 960,600 C 850,550 800,700 700,750 C 650,800 750,800 960,800 Z" fill="#dcfce7" opacity="0.7" />
          <path d="M 700,-50 C 750,50 850,150 800,250 C 700,300 600,200 700,-50 Z" fill="#dcfce7" opacity="0.7" />

          {/* Grid overlay */}
          <rect width="100%" height="100%" fill="url(#grid-large)" />
          
          {/* Diagonal roads / highways */}
          <path d="M -100,200 L 1200,800" fill="none" stroke="#ffffff" strokeWidth="4" opacity="0.7"/>
          <path d="M 200,-100 L 1000,900" fill="none" stroke="#ffffff" strokeWidth="6" opacity="0.7"/>
          <path d="M 800,-100 L 100,900" fill="none" stroke="#ffffff" strokeWidth="3" opacity="0.7"/>
          <path d="M 1000,-100 L 500,900" fill="none" stroke="#ffffff" strokeWidth="5" opacity="0.7"/>
        </svg>

        {/* Legend */}
        <div className="absolute top-6 right-6 bg-white/95 backdrop-blur-md rounded-xl shadow-[0_4px_20px_-4px_rgba(0,0,0,0.1)] border border-slate-100 p-4 min-w-[170px] z-20">
          <h4 className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-3">Room Type</h4>
          <div className="space-y-3">
            <div className="flex items-center text-xs text-slate-700 font-medium">
              <span className="w-3 h-3 rounded-full bg-[#4f46e5] mr-2.5 shadow-sm ring-1 ring-black/5"></span>
              Entire home/apt
            </div>
            <div className="flex items-center text-xs text-slate-700 font-medium">
              <span className="w-3 h-3 rounded-full bg-green-500 mr-2.5 shadow-sm ring-1 ring-black/5"></span>
              Private room
            </div>
            <div className="flex items-center text-xs text-slate-700 font-medium">
              <span className="w-3 h-3 rounded-full bg-amber-500 mr-2.5 shadow-sm ring-1 ring-black/5"></span>
              Hotel room
            </div>
            <div className="flex items-center text-xs text-slate-700 font-medium">
              <span className="w-3 h-3 rounded-full bg-red-500 mr-2.5 shadow-sm ring-1 ring-black/5"></span>
              Shared room
            </div>
          </div>
        </div>

        {/* Map UI Controls (zoom, etc) */}
        <div className="absolute bottom-8 right-6 flex flex-col space-y-2 z-20">
          <button className="w-9 h-9 bg-white rounded-lg shadow-md border border-slate-100 flex items-center justify-center text-slate-600 hover:text-slate-900 transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 5v14M5 12h14"/></svg>
          </button>
          <button className="w-9 h-9 bg-white rounded-lg shadow-md border border-slate-100 flex items-center justify-center text-slate-600 hover:text-slate-900 transition-colors">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M5 12h14"/></svg>
          </button>
        </div>

        {/* Map Markers Overlay */}
        <div className="absolute inset-0 z-10 pointer-events-none">
          {/* Clusters */}
          <div className="absolute top-[22%] left-[32%] w-10 h-10 bg-[#4f46e5] rounded-full flex items-center justify-center text-white font-bold text-sm ring-2 ring-white shadow-lg pointer-events-auto cursor-pointer hover:bg-indigo-700 hover:scale-105 transition-all">
            42
          </div>
          <div className="absolute top-[45%] left-[55%] w-12 h-12 bg-[#4f46e5] rounded-full flex items-center justify-center text-white font-bold text-base ring-2 ring-white shadow-lg pointer-events-auto cursor-pointer hover:bg-indigo-700 hover:scale-105 transition-all">
            128
          </div>
          <div className="absolute top-[68%] left-[28%] w-9 h-9 bg-[#4f46e5] rounded-full flex items-center justify-center text-white font-bold text-xs ring-2 ring-white shadow-lg pointer-events-auto cursor-pointer hover:bg-indigo-700 hover:scale-105 transition-all">
            15
          </div>
          <div className="absolute top-[75%] left-[72%] w-11 h-11 bg-[#4f46e5] rounded-full flex items-center justify-center text-white font-bold text-sm ring-2 ring-white shadow-lg pointer-events-auto cursor-pointer hover:bg-indigo-700 hover:scale-105 transition-all">
            86
          </div>
          <div className="absolute top-[18%] left-[78%] w-8 h-8 bg-[#4f46e5] rounded-full flex items-center justify-center text-white font-bold text-xs ring-2 ring-white shadow-lg pointer-events-auto cursor-pointer hover:bg-indigo-700 hover:scale-105 transition-all">
            7
          </div>

          {/* Individual Markers - Entire Home (Indigo) */}
          <div className="absolute top-[38%] left-[45%] w-2.5 h-2.5 bg-[#4f46e5] rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[41%] left-[48%] w-2.5 h-2.5 bg-[#4f46e5] rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[49%] left-[51%] w-2.5 h-2.5 bg-[#4f46e5] rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[52%] left-[60%] w-2.5 h-2.5 bg-[#4f46e5] rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[30%] left-[25%] w-2.5 h-2.5 bg-[#4f46e5] rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[70%] left-[60%] w-2.5 h-2.5 bg-[#4f46e5] rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[80%] left-[45%] w-2.5 h-2.5 bg-[#4f46e5] rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>

          {/* Individual Markers - Private Room (Green) */}
          <div className="absolute top-[42%] left-[59%] w-2.5 h-2.5 bg-green-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[46%] left-[62%] w-2.5 h-2.5 bg-green-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[55%] left-[50%] w-2.5 h-2.5 bg-green-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[25%] left-[35%] w-2.5 h-2.5 bg-green-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[82%] left-[75%] w-2.5 h-2.5 bg-green-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>

          {/* Individual Markers - Hotel Room (Amber) */}
          <div className="absolute top-[44%] left-[52%] w-2.5 h-2.5 bg-amber-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[48%] left-[58%] w-2.5 h-2.5 bg-amber-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[68%] left-[30%] w-2.5 h-2.5 bg-amber-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>

          {/* Individual Markers - Shared Room (Red) */}
          <div className="absolute top-[50%] left-[55%] w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
          <div className="absolute top-[72%] left-[68%] w-2.5 h-2.5 bg-red-500 rounded-full ring-2 ring-white shadow-sm pointer-events-auto cursor-pointer hover:scale-150 transition-transform"></div>
        </div>

        {/* Selected Marker Popup (Mockup) */}
        <div className="absolute top-[37%] left-[46%] z-30 transform -translate-x-1/2 -translate-y-full pb-3 pointer-events-none">
          <div className="bg-white rounded-xl shadow-[0_10px_30px_-5px_rgba(0,0,0,0.15)] p-3 w-56 border border-slate-100 pointer-events-auto relative">
            <div className="aspect-[4/3] bg-slate-100 rounded-lg mb-3 overflow-hidden relative border border-slate-100">
              <div className="absolute inset-0 bg-gradient-to-br from-slate-200 to-slate-100 flex items-center justify-center">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-slate-400">
                  <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                  <polyline points="9 22 9 12 15 12 15 22"></polyline>
                </svg>
              </div>
              <div className="absolute top-2 right-2 bg-white/95 backdrop-blur shadow-sm rounded-md px-1.5 py-0.5 text-[11px] font-bold text-slate-700 flex items-center gap-1">
                <span>★</span> 4.9
              </div>
            </div>
            <div className="flex justify-between items-start mb-1">
              <h5 className="text-[13px] font-semibold text-slate-900 truncate pr-2">Modern Loft Studio</h5>
            </div>
            <p className="text-[11px] text-slate-500 mb-2 font-medium">Entire home &middot; 2 beds</p>
            <p className="text-sm font-bold text-slate-900">$145<span className="text-[11px] font-medium text-slate-500"> / night</span></p>

            {/* Caret attached directly to the box */}
            <div className="absolute -bottom-[6px] left-1/2 -translate-x-1/2 w-3.5 h-3.5 bg-white border-b border-r border-slate-100 transform rotate-45 shadow-[3px_3px_5px_rgba(0,0,0,0.02)]"></div>
          </div>
        </div>
      </div>
    </div>
  );
}
