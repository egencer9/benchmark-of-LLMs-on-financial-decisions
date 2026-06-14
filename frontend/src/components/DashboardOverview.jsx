import React from 'react';
import { TrendingUp, Play, Trash2, Sliders } from 'lucide-react';
import {
  ResponsiveContainer,
  LineChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Line
} from 'recharts';

export default function DashboardOverview({
  configData,
  exchange,
  historyList,
  historyTotal,
  historyPage,
  setHistoryPage,
  selectedRunsForCompare,
  toggleCompareRun,
  formatRunCapital,
  formatCurrency,
  formatDateStr,
  loadRunDetails,
  setSubTab,
  deleteRun,
  compareData,
  chartGridColor,
  chartAxisColor,
  chartTooltipBg,
  chartTooltipBorder,
  chartTooltipColor,
  COLORS,
  currencyCode,
  totalPages,
  getPageNumbers
}) {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header Metrics Panel */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-card border border-border p-6 rounded-xl flex flex-col justify-between h-32 hover:border-slate-800 transition-all">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Exchange Tickers Tracked</span>
          <span className="text-2xl font-black font-mono text-slate-200">{configData?.exchanges[exchange]?.tickers_count || 0} Stocks</span>
          <span className="text-[10px] text-slate-400">All data loaded from local datasets</span>
        </div>
        
        <div className="bg-card border border-border p-6 rounded-xl flex flex-col justify-between h-32 hover:border-slate-800 transition-all">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Runs History Count</span>
          <span className="text-2xl font-black font-mono text-slate-200">{historyTotal} Simulations</span>
          <span className="text-[10px] text-slate-400">Filterable by model date ranges</span>
        </div>

        <div className="bg-card border border-border p-6 rounded-xl flex flex-col justify-between h-32 hover:border-slate-800 transition-all">
          <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Active Models Evaluated</span>
          <span className="text-2xl font-black font-mono text-slate-200">{configData?.models.length || 0} Agent Configurations</span>
          <span className="text-[10px] text-slate-400">OpenRouter LLM interfaces</span>
        </div>
      </div>

      {/* Primary Chart Visualization */}
      <div className="bg-card border border-border p-6 rounded-xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Comparative Portfolio Performance Chart</h3>
            <p className="text-[11px] text-slate-500 mt-1">Select runs in the History Ledger table below to overlay and evaluate cumulative return curves.</p>
          </div>

          <div className="flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500"></span>
            <span className="text-[10px] text-slate-400 font-mono">End-to-End Equity Curves ({currencyCode})</span>
          </div>
        </div>

        {compareData.length > 0 ? (
          <div className="h-80 w-full font-mono text-[10px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={compareData}>
                <CartesianGrid strokeDasharray="3 3" stroke={chartGridColor} />
                <XAxis
                  dataKey="date"
                  stroke={chartAxisColor}
                  tickFormatter={(v) => v || ''}
                />
                <YAxis
                  stroke={chartAxisColor}
                  tickFormatter={(v) => formatCurrency(v)}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: chartTooltipBg,
                    border: `1px solid ${chartTooltipBorder}`,
                    color: chartTooltipColor
                  }}
                  formatter={(value, name) => [formatCurrency(value), name]}
                />
                <Legend />
                {selectedRunsForCompare.map((fname, idx) => {
                  const runMeta = historyList.find(h => h.filename === fname);
                  const label = runMeta ? `${runMeta.alias} (${runMeta.trading_approach || runMeta.prompt_version || 'Balanced'})` : fname;
                  return (
                    <Line
                      key={fname}
                      type="monotone"
                      dataKey={label}
                      stroke={COLORS[idx % COLORS.length]}
                      strokeWidth={2.5}
                      dot={false}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          /* Dashboard Empty State when no compare items selected */
          <div className="h-80 border border-dashed border-border rounded-lg flex flex-col justify-center items-center text-center p-8 bg-slate-950/20">
            <div className="p-4 bg-slate-900 border border-border text-slate-400 rounded-full mb-4">
              <TrendingUp className="h-8 w-8 text-blue-500" />
            </div>
            <h4 className="text-sm font-bold text-slate-300">No Simulation Runs Overlayed</h4>
            <p className="text-xs text-slate-500 max-w-sm mt-2">
              Select one or more historical benchmark runs from the checklist in the Saved Runs History Ledger table below to visualize comparative portfolio performance.
            </p>
            {historyList.length === 0 && (
              <button
                onClick={() => setSubTab('runner')}
                className="mt-4 flex items-center gap-2 bg-blue-600/80 hover:bg-blue-600 text-slate-100 px-4 py-2 rounded text-xs font-bold transition-all"
              >
                <Play className="h-3.5 w-3.5" /> Execute First Simulation
              </button>
            )}
          </div>
        )}
      </div>

      {/* Compare Selection checklist Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-card border border-border p-6 rounded-xl">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Saved Runs History Ledger</h3>
          
          {historyList.length === 0 ? (
            <div className="py-12 text-center text-xs text-slate-500">
              No historical run files found. Run a simulation in the Backtest Runner first.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="border-b border-border text-slate-500 uppercase tracking-wider text-[10px] font-mono">
                    <th className="py-2.5 px-3">Compare</th>
                    <th className="py-2.5 px-3">Model Alias</th>
                    <th className="py-2.5 px-3">Approach</th>
                    <th className="py-2.5 px-3">Init. Capital</th>
                    <th className="py-2.5 px-3">Final Capital</th>
                    <th className="py-2.5 px-3">PnL</th>
                    <th className="py-2.5 px-3">Run Dates</th>
                    <th className="py-2.5 px-3">Max DD</th>
                    <th className="py-2.5 px-3 font-mono">Sharpe</th>
                    <th className="py-2.5 px-3 font-mono">Win Rate</th>
                    <th className="py-2.5 px-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {historyList.map(run => (
                    <tr key={run.filename} className="hover:bg-slate-800/40 transition-all font-mono">
                      <td className="py-3 px-3">
                        <input
                          type="checkbox"
                          checked={selectedRunsForCompare.includes(run.filename)}
                          onChange={() => toggleCompareRun(run.filename)}
                          className="h-4 w-4 bg-slate-900 border-border rounded text-blue-600 accent-blue-600 cursor-pointer"
                        />
                      </td>
                      <td className="py-3 px-3 font-bold text-slate-300">{run.alias}</td>
                      <td className="py-3 px-3 text-slate-400">{run.trading_approach || 'Balanced'}</td>
                      <td className="py-3 px-3 text-slate-400">{formatRunCapital(run)}</td>
                      <td className="py-3 px-3 text-slate-300 font-bold">{formatCurrency(run.final_capital)}</td>
                      <td className={`py-3 px-3 font-bold ${run.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {run.pnl >= 0 ? '+' : ''}{formatCurrency(run.pnl)}
                      </td>
                      <td className="py-3 px-3 text-amber-100 font-mono">
                        {run.date_range && run.date_range.length === 2
                          ? `${formatDateStr(run.date_range[0])} - ${formatDateStr(run.date_range[1])}`
                          : '-'}
                      </td>
                      <td className="py-3 px-3 text-orange-500 font-mono">{run.metrics?.["Max Drawdown"] || '0.00%'}</td>
                      <td className="py-3 px-3 text-amber-400">{run.metrics?.["Sharpe Ratio"] || '-'}</td>
                      <td className="py-3 px-3 text-blue-400">{run.metrics?.["Win Rate"] || '-'}</td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => {
                              loadRunDetails(run.filename);
                              setSubTab('insights');
                            }}
                            className="bg-slate-800/80 border border-slate-700/60 text-slate-300 font-medium px-2 py-1 rounded text-[10px] tracking-wide hover:bg-slate-700 hover:text-slate-100 transition-all cursor-pointer"
                          >
                            View Details
                          </button>
                          <button
                            onClick={() => deleteRun(run.filename)}
                            className="p-1.5 bg-rose-600/10 hover:bg-rose-600/20 text-rose-500 border border-rose-500/20 hover:border-rose-500/35 rounded transition-all cursor-pointer flex items-center justify-center"
                            title="Delete Run"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-border/60 pt-4 mt-4 text-xs font-mono">
              <span className="text-slate-500">
                Showing {Math.min((historyPage - 1) * 20 + 1, historyTotal)} - {Math.min(historyPage * 20, historyTotal)} of {historyTotal} runs
              </span>
              
              <div className="flex items-center gap-1">
                <button
                  disabled={historyPage === 1}
                  onClick={() => setHistoryPage(prev => Math.max(prev - 1, 1))}
                  className="px-2.5 py-1 rounded bg-slate-900 border border-border text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:hover:text-slate-400 disabled:cursor-not-allowed transition-all cursor-pointer"
                >
                  Prev
                </button>
                
                {getPageNumbers().map((p, idx) => (
                  p === '...' ? (
                    <span key={`dots-${idx}`} className="px-1.5 text-slate-600">...</span>
                  ) : (
                    <button
                      key={p}
                      onClick={() => setHistoryPage(p)}
                      className={`px-2.5 py-1 rounded transition-all cursor-pointer font-bold ${
                        historyPage === p
                          ? 'bg-blue-600 text-slate-100 font-extrabold'
                          : 'bg-slate-900 border border-border text-slate-400 hover:text-slate-200'
                      }`}
                    >
                      {p}
                    </button>
                  )
                ))}
                
                <button
                  disabled={historyPage === totalPages}
                  onClick={() => setHistoryPage(prev => Math.min(prev + 1, totalPages))}
                  className="px-2.5 py-1 rounded bg-slate-900 border border-border text-slate-400 hover:text-slate-200 disabled:opacity-40 disabled:hover:text-slate-400 disabled:cursor-not-allowed transition-all cursor-pointer"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right comparison metrics cards */}
        <div className="bg-card border border-border p-6 rounded-xl">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Direct Run Metrics Diffs</h3>
          
          {selectedRunsForCompare.length === 0 ? (
            <div className="h-64 flex flex-col justify-center items-center text-center text-xs text-slate-500 border border-dashed border-border rounded">
              <Sliders className="h-6 w-6 text-slate-600 mb-2" />
              <span>Select runs to compare</span>
            </div>
          ) : (
            <div className="space-y-4">
              {selectedRunsForCompare.map((fname, idx) => {
                const run = historyList.find(h => h.filename === fname);
                if (!run) return null;
                const dateRangeStr = run.date_range && run.date_range.length === 2
                  ? `${formatDateStr(run.date_range[0])}\n-\n${formatDateStr(run.date_range[1])}`
                  : 'N/A';
                const runPnl = run.pnl || 0;
                return (
                  <div key={fname} className="p-4 rounded-lg bg-slate-950/60 border border-border animate-fade-in">
                    <div className="flex items-center gap-2 mb-2">
                      <div className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
                      <span className="font-bold text-xs truncate text-slate-200">{run.alias} ({run.trading_approach || 'Balanced'})</span>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-2 text-center mt-2 pt-2 border-t border-white/5 items-center">
                      <div>
                        <div className="text-[9px] text-slate-500 uppercase tracking-wider font-bold">Dates</div>
                        <div className="text-[10px] font-bold text-amber-100 font-mono mt-0.5 whitespace-pre-line leading-tight">{dateRangeStr}</div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-500 uppercase tracking-wider font-bold">Max DD</div>
                        <div className="text-xs font-bold text-orange-500 font-mono mt-0.5">{run.metrics?.["Max Drawdown"] || '0.00%'}</div>
                      </div>
                      <div>
                        <div className="text-[9px] text-slate-500 uppercase tracking-wider font-bold">PnL</div>
                        <div className={`text-xs font-bold font-mono mt-0.5 ${runPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {runPnl >= 0 ? '+' : ''}{formatCurrency(runPnl)}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
