import React from 'react';
import { FolderOpen, Activity } from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export default function ModelInsights({
  selectedHistoryFile,
  loadRunDetails,
  historyList,
  singleRunDetails,
  chartGridColor,
  chartAxisColor,
  chartTooltipBg,
  chartTooltipBorder,
  chartTooltipColor,
  formatCurrency,
  COLORS
}) {
  // Allocation donut data helper (from latest day of active run details)
  const getAllocationData = () => {
    if (!singleRunDetails || !singleRunDetails.detailed_history) return [];
    const latestDay = singleRunDetails.detailed_history[singleRunDetails.detailed_history.length - 1];
    if (!latestDay) return [];

    const data = [
      { name: 'Free Cash', value: latestDay.cash || 0 },
      { name: 'Margin Posted', value: latestDay.margin_posted || 0 }
    ];
    return data.filter(d => d.value > 0);
  };

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Target Run selector */}
      <div className="bg-card border border-border p-6 rounded-xl flex items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <FolderOpen className="h-5 w-5 text-blue-500" />
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Select Run Insights Target</h3>
            <p className="text-[10px] text-slate-500 mt-0.5">Choose a saved run simulation to explore detailed daily assets allocation balances.</p>
          </div>
        </div>

        <select
          value={selectedHistoryFile}
          onChange={(e) => loadRunDetails(e.target.value)}
          className="bg-slate-900 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2 outline-none cursor-pointer"
        >
          <option value="" disabled>-- Select a run --</option>
          {historyList.map(h => (
            <option key={h.filename} value={h.filename}>{h.alias} ({h.timestamp})</option>
          ))}
        </select>
      </div>

      {!singleRunDetails ? (
        <div className="bg-card border border-border rounded-xl p-16 flex flex-col justify-center items-center text-center">
          <Activity className="h-10 w-10 text-slate-600 mb-4" />
          <h4 className="text-sm font-bold text-slate-300">No Run Selected for Insights</h4>
          <p className="text-xs text-slate-500 max-w-sm mt-2">
            Please select an executed backtest run from the dropdown menu above to review detailed holdings allocations.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fade-in">
          {/* Left details grid */}
          <div className="lg:col-span-2 space-y-8">
            {/* Detailed Cash vs Equity Area Chart */}
            <div className="bg-card border border-border p-6 rounded-xl">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6">Daily Cash vs Equity Value Breakdown</h3>
              
              <div className="h-80 w-full font-mono text-[10px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={singleRunDetails.detailed_history}>
                    <defs>
                      <linearGradient id="colorCash" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.2}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                    <XAxis dataKey="date" stroke={chartAxisColor} />
                    <YAxis stroke={chartAxisColor} tickFormatter={(v) => formatCurrency(v)} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: chartTooltipBg,
                        border: `1px solid ${chartTooltipBorder}`,
                        color: chartTooltipColor
                      }}
                      formatter={(value) => [formatCurrency(value)]}
                    />
                    <Legend />
                    <Area type="monotone" name="Uninvested Cash" dataKey="cash" stroke="#3b82f6" fillOpacity={1} fill="url(#colorCash)" />
                    <Area type="monotone" name="Total Net Worth" dataKey="total_value" stroke="#10b981" fillOpacity={1} fill="url(#colorTotal)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Details specs */}
            <div className="bg-card border border-border p-6 rounded-xl grid grid-cols-3 gap-6 text-center">
              <div className="border-r border-border">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Model Engine</span>
                <div className="text-sm font-black text-slate-200 mt-1 truncate px-2">{singleRunDetails.alias}</div>
              </div>
              <div className="border-r border-border">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">Initial Capital</span>
                <div className="text-sm font-black text-slate-200 mt-1 font-mono">{formatCurrency(singleRunDetails.detailed_history?.[0]?.total_value || 1000000)}</div>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">End Net Worth</span>
                <div className="text-sm font-black text-emerald-400 mt-1 font-mono">
                  {formatCurrency(singleRunDetails.detailed_history?.[singleRunDetails.detailed_history.length - 1]?.total_value)}
                </div>
              </div>
            </div>
          </div>

          {/* Right side allocation donut */}
          <div className="space-y-8">
            <div className="bg-card border border-border p-6 rounded-xl flex flex-col items-center">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider self-start mb-6">Ending Assets Allocation</h3>

              <div className="h-64 w-full flex items-center justify-center font-mono text-[10px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={getAllocationData()}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={85}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {getAllocationData().map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: chartTooltipBg,
                        border: `1px solid ${chartTooltipBorder}`,
                        color: chartTooltipColor
                      }}
                      formatter={(value) => formatCurrency(value)}
                    />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Ticker holdings list table */}
            <div className="bg-card border border-border p-6 rounded-xl">
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Futures Position Ledger</h3>
              
              <div className="space-y-3 font-mono text-xs">
                {Object.entries(singleRunDetails.detailed_history?.[singleRunDetails.detailed_history.length - 1]?.holdings || {}).length === 0 ? (
                  <div className="text-center py-6 text-slate-500 text-[11px]">
                    Zero active futures positions (100% Cash allocation).
                  </div>
                ) : (
                  Object.entries(singleRunDetails.detailed_history[singleRunDetails.detailed_history.length - 1].holdings).map(([ticker, contracts], idx) => {
                    const parts = ticker.split('_');
                    const displayTicker = parts[0];
                    const positionType = parts[1] || 'LONG';
                    const unrealizedPnl = singleRunDetails.detailed_history[singleRunDetails.detailed_history.length - 1].unrealized_pnl || 0;
                    return (
                      <div key={ticker} className="flex justify-between items-center p-2.5 rounded bg-slate-950/40 border border-border/40">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-200 text-xs">{displayTicker}</span>
                            <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold ${positionType === 'LONG' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'}`}>
                              {positionType}
                            </span>
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">{contracts.toLocaleString()} Contracts</div>
                        </div>
                        <div className="text-right">
                          <div className={`text-xs font-bold ${unrealizedPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                            PnL: {formatCurrency(unrealizedPnl)}
                          </div>
                          <div className="text-[9px] text-slate-500">
                            Margin: {formatCurrency(singleRunDetails.detailed_history[singleRunDetails.detailed_history.length - 1].margin_posted || 0)}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
