import React, { useRef, useEffect } from 'react';
import { Sliders, Database, X, Play, Cpu, AlertTriangle, Activity } from 'lucide-react';

export default function BacktestRunner({
  runnerStatus,
  selectedModelIndex,
  setSelectedModelIndex,
  configData,
  tradingApproach,
  setTradingApproach,
  startDateInput,
  setStartDateInput,
  endDateInput,
  setEndDateInput,
  initialCashInput,
  setInitialCashInput,
  currencySymbol,
  cacheStatus,
  exchange,
  fetchCacheStatus,
  loadingCache,
  cancelBacktest,
  startBacktest,
  runnerProgress,
  runnerLogs,
  runnerExitCode
}) {
  const logsEndRef = useRef(null);

  // Auto-scroll log console when logs update
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'auto' });
    }
  }, [runnerLogs]);

  const exchCache = cacheStatus?.[exchange];
  const mktMeta = exchCache?.market;
  const newsMeta = exchCache?.news;

  // Determine if selected dates are within cache
  const isCached = (meta, dateStr) => {
    if (!meta || !dateStr) return null;
    const d = new Date(dateStr);
    const s = new Date(meta.start);
    const e = new Date(meta.end);
    return d >= s && d <= e;
  };

  const startInCache = isCached(mktMeta, startDateInput);
  const endInCache = isCached(mktMeta, endDateInput);
  const fullyInCache = startInCache && endInCache;
  const partiallyInCache = (startInCache || endInCache) && !fullyInCache;

  return (
    <div className="space-y-8 animate-fade-in">
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Parameter settings panel */}
        <div className="bg-card border border-border p-6 rounded-xl h-fit">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6 flex items-center gap-2">
            <Sliders className="h-4 w-4 text-blue-500" />
            <span>Backtest Configuration</span>
          </h3>

          <div className="space-y-5">
            {/* Model Selector */}
            <div>
              <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-2">Target LLM Model Alias</label>
              <select
                value={selectedModelIndex}
                onChange={(e) => setSelectedModelIndex(parseInt(e.target.value))}
                disabled={runnerStatus === 'running'}
                className="w-full bg-slate-950 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2.5 outline-none cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
              >
                {configData?.models.map((model, idx) => (
                  <option key={idx} value={idx}>{model.alias}</option>
                ))}
              </select>
            </div>

            {/* Trading Approach Selector */}
            <div>
              <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-2">Trading Approach</label>
              <select
                value={tradingApproach}
                onChange={(e) => setTradingApproach(e.target.value)}
                disabled={runnerStatus === 'running'}
                className="w-full bg-slate-950 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2.5 outline-none cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="Balanced">Balanced</option>
                <option value="Aggressive">Aggressive</option>
                <option value="Conservative">Conservative</option>
              </select>
            </div>

            {/* Date ranges */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-2">Start Date</label>
                <input
                  type="date"
                  placeholder="YYYY-MM-DD"
                  value={startDateInput}
                  onChange={(e) => setStartDateInput(e.target.value)}
                  disabled={runnerStatus === 'running'}
                  className="w-full bg-slate-950 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2.5 outline-none font-mono disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-2">End Date</label>
                <input
                  type="date"
                  placeholder="YYYY-MM-DD"
                  value={endDateInput}
                  onChange={(e) => setEndDateInput(e.target.value)}
                  disabled={runnerStatus === 'running'}
                  className="w-full bg-slate-950 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2.5 outline-none font-mono disabled:cursor-not-allowed disabled:opacity-50"
                />
              </div>
            </div>

            {/* Initial Cash */}
            <div>
              <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-2">Initial Investment Capital</label>
              <select
                value={initialCashInput}
                onChange={(e) => setInitialCashInput(parseInt(e.target.value))}
                disabled={runnerStatus === 'running'}
                className="w-full bg-slate-950 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2.5 outline-none cursor-pointer disabled:cursor-not-allowed disabled:opacity-50 font-mono"
              >
                {[10000, 25000, 50000, 100000, 250000, 500000, 1000000].map(val => (
                  <option key={val} value={val}>
                    {val.toLocaleString('de-DE')}{currencySymbol}{val === 100000 ? ' (★)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Cache Status Widget */}
            <div className="bg-slate-950/60 border border-border rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  <Database className="h-3 w-3" />
                  Data Cache Status
                </div>
                <button
                  onClick={fetchCacheStatus}
                  disabled={loadingCache}
                  type="button"
                  className="text-[9px] text-slate-600 hover:text-blue-400 transition-colors font-bold uppercase tracking-wider"
                >
                  {loadingCache ? '...' : 'Refresh'}
                </button>
              </div>

              {!mktMeta ? (
                <div className="text-[10px] text-slate-600 font-mono">No cache found for {exchange}</div>
              ) : (
                <div className="space-y-1.5 font-mono">
                  <div className="flex justify-between items-center">
                    <span className="text-[9px] text-slate-600 uppercase">Market</span>
                    <span className="text-[9px] text-slate-500">{mktMeta.start} → {mktMeta.end}</span>
                  </div>
                  {newsMeta && (
                    <div className="flex justify-between items-center">
                      <span className="text-[9px] text-slate-600 uppercase">News</span>
                      <span className="text-[9px] text-slate-500">{newsMeta.start} → {newsMeta.end}</span>
                    </div>
                  )}
                  {(startDateInput || endDateInput) && (
                    <div className={`mt-2 px-2 py-1.5 rounded text-[10px] font-bold flex items-center gap-1.5 ${
                      fullyInCache
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : partiallyInCache
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                    }`}>
                      <span className="text-base leading-none">
                        {fullyInCache ? '✓' : partiallyInCache ? '~' : '↓'}
                      </span>
                      <span>
                        {fullyInCache
                          ? 'Fully cached — no download needed'
                          : partiallyInCache
                          ? 'Partial cache — missing dates will be fetched'
                          : 'Not cached — will download from yfinance'}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Trigger Buttons */}
            {runnerStatus === 'running' ? (
              <div className="space-y-2">
                <button
                  onClick={cancelBacktest}
                  className="w-full py-3 bg-rose-600 hover:bg-rose-500 text-slate-100 font-bold rounded-lg text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2"
                >
                  <X className="h-4 w-4 animate-pulse" />
                  <span>Cancel Active Run</span>
                </button>
                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider text-center pt-2">
                  Locked State: Running in progress...
                </div>
              </div>
            ) : (
              <button
                onClick={startBacktest}
                className="w-full py-3 bg-blue-600 hover:bg-blue-500 text-slate-100 font-bold rounded-lg text-xs uppercase tracking-wider transition-all flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20"
              >
                <Play className="h-4 w-4" />
                <span>Execute Backtest</span>
              </button>
            )}
          </div>
        </div>

        {/* Log stream console output */}
        <div className="lg:col-span-2 bg-card border border-border p-6 rounded-xl flex flex-col h-[520px]">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex justify-between items-center">
            <span>Real-Time Logs & Progress Stream</span>
            {runnerStatus === 'running' && (
              <span className="text-[10px] font-mono text-slate-500 animate-pulse uppercase">Day {runnerProgress.current_day}/{runnerProgress.total_days}</span>
            )}
          </h3>

          {/* Progress slider bar */}
          {runnerStatus === 'running' && (
            <div className="mb-4 bg-slate-950 p-3 rounded-lg border border-border animate-fade-in flex items-center gap-4">
              <div className="flex-1 bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-emerald-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${runnerProgress.percent}%` }}
                ></div>
              </div>
              <span className="text-xs font-mono font-bold text-emerald-400 shrink-0">{runnerProgress.percent}%</span>
            </div>
          )}

          {/* Monospace Log console box */}
          <div className="flex-1 bg-slate-900 border border-border rounded-lg p-4 font-mono text-xs overflow-y-auto text-slate-400 flex flex-col space-y-1.5 relative">
            {runnerLogs.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-600 text-xs px-8">
                <Cpu className="h-8 w-8 text-slate-700 mb-2" />
                <span>Simulation Log terminal is empty. Trigger a run to steam output logs.</span>
              </div>
            ) : (
              runnerLogs.map((logLine, idx) => (
                <div key={idx} className="whitespace-pre-wrap leading-relaxed break-words">
                  {logLine}
                </div>
              ))
            )}
            
            {/* Auto-scroll anchor */}
            <div ref={logsEndRef}></div>
          </div>

          {/* Exit code warnings (Failure State rendering) */}
          {runnerStatus === 'finished' && (
            <div className="mt-4 p-3 bg-emerald-950/30 border border-emerald-500/20 text-emerald-400 rounded-lg text-xs font-bold flex items-center gap-2 animate-fade-in">
              <Activity className="h-4 w-4" />
              <span>Simulation run finished successfully with Exit Code 0. Result data written to log database.</span>
            </div>
          )}
          {runnerStatus === 'failed' && (
            <div className="mt-4 p-3 bg-rose-950/30 border border-rose-500/20 text-rose-400 rounded-lg text-xs font-bold flex items-center gap-2 animate-fade-in">
              <AlertTriangle className="h-4 w-4" />
              <span>Simulation run terminated or failed (Exit code: {runnerExitCode || 'CRASHED'}). See log messages above.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
