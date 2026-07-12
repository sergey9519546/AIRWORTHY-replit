import React from 'react';

export default function DarkAnalytics() {
  return (
    <div className="w-[1280px] h-[800px] flex overflow-hidden bg-black text-white font-sans selection:bg-[#10b981] selection:text-black">
      {/* SIDEBAR */}
      <div className="w-[320px] h-full bg-[#0f1117] border-t-4 border-[#10b981] flex flex-col flex-shrink-0 z-10 shadow-[4px_0_24px_rgba(0,0,0,0.5)]">
        
        {/* Header */}
        <div className="p-6 border-b border-white/5">
          <div className="flex items-center justify-between mb-1">
            <h1 className="font-mono text-xl font-bold tracking-tight text-white flex items-center gap-2">
              AIRBNB INTEL
            </h1>
            <div className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#10b981] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-[#10b981]"></span>
            </div>
          </div>
          <p className="text-[11px] text-slate-400 font-mono tracking-wide uppercase">CA & FL Market Explorer</p>
        </div>

        {/* Live Metrics Strip */}
        <div className="px-5 py-4 border-b border-white/5 bg-black/40">
          <div className="flex gap-2">
            <div className="flex-1 bg-[#1a1f2e] p-2.5 rounded border border-white/5 relative overflow-hidden group hover:border-[#10b981]/50 transition-colors">
              <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none" />
              <div className="text-[#10b981] text-[9px] font-mono mb-1.5 font-semibold tracking-wider">LISTINGS</div>
              <div className="text-white text-sm font-mono font-bold tracking-tight">96,459</div>
            </div>
            <div className="flex-1 bg-[#1a1f2e] p-2.5 rounded border border-white/5 relative overflow-hidden group hover:border-[#10b981]/50 transition-colors">
              <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none" />
              <div className="text-[#10b981] text-[9px] font-mono mb-1.5 font-semibold tracking-wider">MARKETS</div>
              <div className="text-white text-sm font-mono font-bold tracking-tight">9</div>
            </div>
            <div className="flex-1 bg-[#1a1f2e] p-2.5 rounded border border-white/5 relative overflow-hidden group hover:border-[#10b981]/50 transition-colors">
              <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none" />
              <div className="text-[#10b981] text-[9px] font-mono mb-1.5 font-semibold tracking-wider">AVG/NIGHT</div>
              <div className="text-white text-sm font-mono font-bold tracking-tight">$401</div>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="p-6 border-b border-white/5 flex-1 overflow-y-auto">
          <div className="flex items-center gap-3 mb-6">
            <h2 className="font-mono text-xs font-bold tracking-widest text-slate-300">FILTERS</h2>
            <div className="h-px bg-gradient-to-r from-[#10b981]/80 to-transparent flex-1"></div>
          </div>

          <div className="space-y-5">
            {/* State */}
            <div>
              <label className="block text-[10px] font-mono text-slate-400 mb-2 uppercase tracking-wider">State</label>
              <div className="relative">
                <select className="w-full bg-[#1a1f2e] border border-[#2d3748] text-slate-200 text-xs rounded px-3 py-2.5 outline-none focus:border-[#10b981] focus:ring-1 focus:ring-[#10b981] appearance-none font-mono hover:bg-[#1f2537] transition-colors cursor-pointer">
                  <option>California (CA)</option>
                  <option>Florida (FL)</option>
                  <option>Texas (TX)</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400">
                  <svg className="fill-current h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                    <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                  </svg>
                </div>
              </div>
            </div>

            {/* City */}
            <div>
              <label className="block text-[10px] font-mono text-slate-400 mb-2 uppercase tracking-wider">City / Region</label>
              <div className="relative">
                <select className="w-full bg-[#1a1f2e] border border-[#2d3748] text-slate-200 text-xs rounded px-3 py-2.5 outline-none focus:border-[#10b981] focus:ring-1 focus:ring-[#10b981] appearance-none font-mono hover:bg-[#1f2537] transition-colors cursor-pointer">
                  <option>Los Angeles</option>
                  <option>San Francisco</option>
                  <option>San Diego</option>
                  <option>Orange County</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400">
                  <svg className="fill-current h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                    <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                  </svg>
                </div>
              </div>
            </div>

            {/* Room Type */}
            <div>
              <label className="block text-[10px] font-mono text-slate-400 mb-2 uppercase tracking-wider">Room Type</label>
              <div className="relative">
                <select className="w-full bg-[#1a1f2e] border border-[#2d3748] text-slate-200 text-xs rounded px-3 py-2.5 outline-none focus:border-[#10b981] focus:ring-1 focus:ring-[#10b981] appearance-none font-mono hover:bg-[#1f2537] transition-colors cursor-pointer">
                  <option>All Types</option>
                  <option>Entire home/apt</option>
                  <option>Private room</option>
                  <option>Shared room</option>
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-3 text-slate-400">
                  <svg className="fill-current h-3.5 w-3.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                    <path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/>
                  </svg>
                </div>
              </div>
            </div>

            {/* Price Range */}
            <div>
              <label className="block text-[10px] font-mono text-slate-400 mb-2 uppercase tracking-wider">Price Range</label>
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <span className="absolute left-3 top-2.5 text-slate-500 font-mono text-xs">$</span>
                  <input type="text" defaultValue="50" className="w-full bg-[#1a1f2e] border border-[#2d3748] text-slate-200 text-xs rounded pl-7 pr-3 py-2.5 outline-none focus:border-[#10b981] focus:ring-1 focus:ring-[#10b981] font-mono hover:bg-[#1f2537] transition-colors" />
                  <span className="absolute right-3 top-3 text-[8px] text-slate-500 font-mono font-bold tracking-widest">MIN</span>
                </div>
                <div className="relative flex-1">
                  <span className="absolute left-3 top-2.5 text-slate-500 font-mono text-xs">$</span>
                  <input type="text" defaultValue="1000" className="w-full bg-[#1a1f2e] border border-[#2d3748] text-slate-200 text-xs rounded pl-7 pr-3 py-2.5 outline-none focus:border-[#10b981] focus:ring-1 focus:ring-[#10b981] font-mono hover:bg-[#1f2537] transition-colors" />
                  <span className="absolute right-3 top-3 text-[8px] text-slate-500 font-mono font-bold tracking-widest">MAX</span>
                </div>
              </div>
            </div>

            <div className="pt-4 flex flex-col gap-3">
              <button className="w-full bg-[#10b981] hover:bg-[#059669] text-black font-mono font-bold py-3 rounded transition-colors text-xs shadow-[0_0_15px_rgba(16,185,129,0.3)] hover:shadow-[0_0_20px_rgba(16,185,129,0.5)] tracking-wide">
                APPLY FILTERS
              </button>
              <button className="w-full bg-transparent border border-[#2d3748] text-[#10b981] hover:border-[#10b981]/50 hover:bg-[#10b981]/10 font-mono py-2.5 rounded transition-colors text-xs font-semibold tracking-wide">
                RESET
              </button>
            </div>
          </div>
        </div>

        {/* Visible Results Section */}
        <div className="p-6 border-b border-white/5 bg-[#0a0e1a]/50">
          <div className="flex justify-between items-end mb-5">
            <h3 className="font-mono text-xs text-white tracking-tight"><span className="text-[#10b981]">1,000</span> listings shown</h3>
            <span className="text-[9px] text-slate-500 font-mono uppercase tracking-widest">Room Dist.</span>
          </div>
          
          <div className="flex items-end gap-1.5 h-14 w-full relative">
            <div className="flex-1 bg-[#10b981] rounded-t opacity-90 relative group hover:opacity-100 cursor-pointer transition-opacity" style={{ height: '80%' }}>
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-[#1a1f2e] border border-[#2d3748] text-white text-[9px] font-mono px-1.5 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 whitespace-nowrap shadow-xl">65% (650)</div>
              <div className="text-center text-[8px] text-slate-400 font-mono absolute -bottom-5 left-0 w-full tracking-widest">ENT</div>
            </div>
            <div className="flex-1 bg-blue-500 rounded-t opacity-80 relative group hover:opacity-100 cursor-pointer transition-opacity" style={{ height: '25%' }}>
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-[#1a1f2e] border border-[#2d3748] text-white text-[9px] font-mono px-1.5 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 whitespace-nowrap shadow-xl">25% (250)</div>
              <div className="text-center text-[8px] text-slate-400 font-mono absolute -bottom-5 left-0 w-full tracking-widest">PRV</div>
            </div>
            <div className="flex-1 bg-purple-500 rounded-t opacity-80 relative group hover:opacity-100 cursor-pointer transition-opacity" style={{ height: '8%' }}>
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-[#1a1f2e] border border-[#2d3748] text-white text-[9px] font-mono px-1.5 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 whitespace-nowrap shadow-xl">8% (80)</div>
              <div className="text-center text-[8px] text-slate-400 font-mono absolute -bottom-5 left-0 w-full tracking-widest">SHR</div>
            </div>
            <div className="flex-1 bg-amber-500 rounded-t opacity-80 relative group hover:opacity-100 cursor-pointer transition-opacity" style={{ height: '2%' }}>
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 bg-[#1a1f2e] border border-[#2d3748] text-white text-[9px] font-mono px-1.5 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity z-10 whitespace-nowrap shadow-xl">2% (20)</div>
              <div className="text-center text-[8px] text-slate-400 font-mono absolute -bottom-5 left-0 w-full tracking-widest">HTL</div>
            </div>
          </div>
          <div className="h-5"></div>
        </div>

        {/* Footer */}
        <div className="p-5 mt-auto text-center bg-[#0a0e1a]/80">
          <p className="text-[9px] text-slate-500 font-mono uppercase tracking-widest leading-relaxed">
            Data sourced from <span className="text-slate-400">InsideAirbnb</span><br/>
            For educational purposes only
          </p>
        </div>
      </div>

      {/* MAP AREA */}
      <div className="flex-1 relative bg-[#05070d] overflow-hidden">
        
        {/* Map Background FX */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-[#111827] via-[#05070d] to-[#000000] opacity-90" />
        <div className="absolute inset-0 opacity-[0.04]" style={{ backgroundImage: 'linear-gradient(#10b981 1px, transparent 1px), linear-gradient(90deg, #10b981 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
        
        {/* Simulated glow of high-density areas */}
        <div className="absolute top-[20%] left-[25%] w-[500px] h-[500px] bg-[#10b981] blur-[150px] rounded-full opacity-5 pointer-events-none" />
        <div className="absolute bottom-[10%] right-[15%] w-[400px] h-[400px] bg-blue-500 blur-[150px] rounded-full opacity-[0.03] pointer-events-none" />

        {/* Marker Clusters */}
        <div className="absolute top-[28%] left-[35%] w-16 h-16 rounded-full bg-[#10b981]/10 border border-[#10b981]/30 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.15)] backdrop-blur-sm hover:bg-[#10b981]/20 transition-all cursor-pointer group z-20 animate-[pulse_4s_ease-in-out_infinite]">
          <div className="w-11 h-11 rounded-full bg-[#10b981]/80 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.5)] group-hover:scale-110 transition-transform">
            <span className="font-mono text-white text-xs font-bold tracking-tight">1.2k</span>
          </div>
        </div>

        <div className="absolute top-[55%] left-[58%] w-20 h-20 rounded-full bg-[#10b981]/10 border border-[#10b981]/30 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.15)] backdrop-blur-sm hover:bg-[#10b981]/20 transition-all cursor-pointer group z-20 animate-[pulse_5s_ease-in-out_infinite_0.5s]">
          <div className="w-14 h-14 rounded-full bg-[#10b981]/90 flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.6)] group-hover:scale-110 transition-transform">
            <span className="font-mono text-white text-sm font-bold tracking-tight">3.4k</span>
          </div>
        </div>

        <div className="absolute top-[35%] left-[75%] w-14 h-14 rounded-full bg-[#10b981]/10 border border-[#10b981]/30 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.15)] backdrop-blur-sm hover:bg-[#10b981]/20 transition-all cursor-pointer group z-20 animate-[pulse_3.5s_ease-in-out_infinite_1s]">
          <div className="w-9 h-9 rounded-full bg-[#10b981]/70 flex items-center justify-center shadow-[0_0_10px_rgba(16,185,129,0.4)] group-hover:scale-110 transition-transform">
            <span className="font-mono text-white text-[11px] font-bold tracking-tight">850</span>
          </div>
        </div>

        <div className="absolute bottom-[25%] left-[25%] w-12 h-12 rounded-full bg-[#10b981]/10 border border-[#10b981]/30 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.15)] backdrop-blur-sm hover:bg-[#10b981]/20 transition-all cursor-pointer group z-20 animate-[pulse_4.5s_ease-in-out_infinite_2s]">
          <div className="w-7 h-7 rounded-full bg-[#10b981]/60 flex items-center justify-center shadow-[0_0_10px_rgba(16,185,129,0.3)] group-hover:scale-110 transition-transform">
            <span className="font-mono text-white text-[9px] font-bold tracking-tight">142</span>
          </div>
        </div>

        {/* Scattered individual properties (dots) */}
        {/* Cluster 1 orbit */}
        <div className="absolute top-[25%] left-[32%] w-2 h-2 rounded-full bg-[#10b981] shadow-[0_0_10px_rgba(16,185,129,1)] opacity-80" />
        <div className="absolute top-[26%] left-[38%] w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,1)] opacity-70" />
        <div className="absolute top-[32%] left-[33%] w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(192,132,252,1)] opacity-90" />
        <div className="absolute top-[31%] left-[39%] w-1.5 h-1.5 rounded-full bg-[#10b981] shadow-[0_0_8px_rgba(16,185,129,1)] opacity-60" />
        <div className="absolute top-[22%] left-[36%] w-1 h-1 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,1)] opacity-80" />

        {/* Cluster 2 orbit */}
        <div className="absolute top-[50%] left-[55%] w-2 h-2 rounded-full bg-[#10b981] shadow-[0_0_10px_rgba(16,185,129,1)] opacity-90" />
        <div className="absolute top-[62%] left-[54%] w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,1)] opacity-70" />
        <div className="absolute top-[60%] left-[64%] w-2 h-2 rounded-full bg-[#10b981] shadow-[0_0_10px_rgba(16,185,129,1)] opacity-100" />
        <div className="absolute top-[52%] left-[63%] w-1.5 h-1.5 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(192,132,252,1)] opacity-80" />
        <div className="absolute top-[65%] left-[59%] w-1 h-1 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,1)] opacity-90" />
        <div className="absolute top-[48%] left-[60%] w-2.5 h-2.5 rounded-full bg-[#10b981] shadow-[0_0_12px_rgba(16,185,129,1)] opacity-100" />
        <div className="absolute top-[57%] left-[53%] w-1 h-1 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,1)] opacity-60" />
        <div className="absolute top-[64%] left-[65%] w-1.5 h-1.5 rounded-full bg-[#10b981] shadow-[0_0_10px_rgba(16,185,129,1)] opacity-80" />

        {/* Scattered randoms */}
        <div className="absolute top-[15%] left-[60%] w-1.5 h-1.5 rounded-full bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,1)] opacity-50" />
        <div className="absolute top-[45%] left-[20%] w-1 h-1 rounded-full bg-[#10b981] shadow-[0_0_8px_rgba(16,185,129,1)] opacity-40" />
        <div className="absolute top-[75%] left-[40%] w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_8px_rgba(192,132,252,1)] opacity-60" />
        <div className="absolute top-[80%] left-[80%] w-1.5 h-1.5 rounded-full bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,1)] opacity-50" />
        <div className="absolute top-[20%] left-[85%] w-2 h-2 rounded-full bg-[#10b981] shadow-[0_0_10px_rgba(16,185,129,1)] opacity-70" />
        <div className="absolute top-[10%] left-[45%] w-1 h-1 rounded-full bg-blue-400 shadow-[0_0_6px_rgba(96,165,250,1)] opacity-40" />


        {/* Map Overlays */}
        
        {/* Top-right legend */}
        <div className="absolute top-6 right-6 w-52 bg-[#0a0e1a]/80 backdrop-blur-md border border-white/10 rounded-lg p-5 shadow-[0_8px_32px_rgba(0,0,0,0.5)] z-30">
          <h3 className="font-mono text-[10px] text-slate-400 mb-4 uppercase tracking-widest font-bold">Property Types</h3>
          <div className="space-y-3.5">
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-3.5 h-3.5">
                <div className="absolute inset-0 rounded-full bg-[#10b981] opacity-40 blur-[2px]"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-[#10b981] relative z-10 shadow-[0_0_8px_rgba(16,185,129,0.8)] border border-white/20"></div>
              </div>
              <span className="text-xs text-slate-200 font-mono tracking-tight">Entire Home</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-3.5 h-3.5">
                <div className="absolute inset-0 rounded-full bg-blue-500 opacity-40 blur-[2px]"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-blue-500 relative z-10 shadow-[0_0_8px_rgba(59,130,246,0.8)] border border-white/20"></div>
              </div>
              <span className="text-xs text-slate-200 font-mono tracking-tight">Private Room</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-3.5 h-3.5">
                <div className="absolute inset-0 rounded-full bg-purple-500 opacity-40 blur-[2px]"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-purple-500 relative z-10 shadow-[0_0_8px_rgba(168,85,247,0.8)] border border-white/20"></div>
              </div>
              <span className="text-xs text-slate-200 font-mono tracking-tight">Shared Room</span>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative flex items-center justify-center w-3.5 h-3.5">
                <div className="absolute inset-0 rounded-full bg-amber-500 opacity-40 blur-[2px]"></div>
                <div className="w-2.5 h-2.5 rounded-full bg-amber-500 relative z-10 shadow-[0_0_8px_rgba(245,158,11,0.8)] border border-white/20"></div>
              </div>
              <span className="text-xs text-slate-200 font-mono tracking-tight">Hotel Room</span>
            </div>
          </div>
        </div>

        {/* Map UI Controls (Zoom etc) mock */}
        <div className="absolute bottom-6 left-6 flex flex-col gap-2 z-30">
          <button className="w-8 h-8 bg-[#1a1f2e]/90 backdrop-blur-sm border border-[#2d3748] rounded flex items-center justify-center text-slate-300 hover:text-white hover:border-[#10b981] transition-colors shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          </button>
          <button className="w-8 h-8 bg-[#1a1f2e]/90 backdrop-blur-sm border border-[#2d3748] rounded flex items-center justify-center text-slate-300 hover:text-white hover:border-[#10b981] transition-colors shadow-lg">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
          </button>
        </div>

        {/* Bottom-right link */}
        <div className="absolute bottom-6 right-6 z-30">
          <button className="bg-[#1a1f2e]/90 backdrop-blur-sm border border-[#2d3748] hover:border-[#10b981] hover:bg-[#1f2537] transition-all text-slate-300 hover:text-white px-5 py-2.5 rounded-full font-mono text-[11px] font-semibold tracking-wide flex items-center gap-3 shadow-[0_4px_20px_rgba(0,0,0,0.5)] group">
            <span className="text-[#10b981] group-hover:-translate-x-1 transition-transform">←</span> 
            REVENUE ESTIMATOR
          </button>
        </div>

        {/* Map Crosshairs/Targeting UI just for aesthetic */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 border border-white/5 rounded-full pointer-events-none flex items-center justify-center">
          <div className="w-1 h-1 bg-white/20 rounded-full"></div>
          <div className="absolute top-0 left-1/2 w-px h-2 bg-white/10 -translate-x-1/2"></div>
          <div className="absolute bottom-0 left-1/2 w-px h-2 bg-white/10 -translate-x-1/2"></div>
          <div className="absolute left-0 top-1/2 h-px w-2 bg-white/10 -translate-y-1/2"></div>
          <div className="absolute right-0 top-1/2 h-px w-2 bg-white/10 -translate-y-1/2"></div>
        </div>

      </div>
    </div>
  );
}
