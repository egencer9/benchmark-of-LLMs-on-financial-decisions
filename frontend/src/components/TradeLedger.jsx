import React, { useState } from 'react';
import { BookOpen, Search, X } from 'lucide-react';

export default function TradeLedger({
  selectedHistoryFile,
  loadRunDetails,
  historyList,
  ledgerActionFilter,
  setLedgerActionFilter,
  ledgerFilter,
  setLedgerFilter,
  singleRunDetails,
  formatCurrency
}) {
  const [selectedTrade, setSelectedTrade] = useState(null);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Controls */}
      <div className="bg-card border border-border p-6 rounded-xl flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <BookOpen className="h-5 w-5 text-blue-500" />
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Executed Trade Transaction Ledger</h3>
            <p className="text-[10px] text-slate-500 mt-0.5">Filter and explore specific agent decisions and click to read the LLM reasoning logs.</p>
          </div>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Select run */}
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

          {/* Filter action type */}
          <select
            value={ledgerActionFilter}
            onChange={(e) => setLedgerActionFilter(e.target.value)}
            className="bg-slate-900 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2 outline-none cursor-pointer"
          >
            <option value="ALL">All Actions</option>
            <option value="LONG">LONG Only</option>
            <option value="SHORT">SHORT Only</option>
            <option value="EXIT">EXIT Only</option>
            <option value="HOLD">HOLD Only</option>
          </select>

          {/* Ticker Search */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search ticker..."
              value={ledgerFilter}
              onChange={(e) => setLedgerFilter(e.target.value)}
              className="bg-slate-900 border border-border rounded-lg text-xs px-4 py-2 pl-9 outline-none text-slate-200 placeholder-slate-500 w-44"
            />
          </div>
        </div>
      </div>

      {!singleRunDetails ? (
        <div className="bg-card border border-border rounded-xl p-16 flex flex-col justify-center items-center text-center">
          <BookOpen className="h-10 w-10 text-slate-600 mb-4" />
          <h4 className="text-sm font-bold text-slate-300">No Run Selected for Ledger</h4>
          <p className="text-xs text-slate-500 max-w-sm mt-2">
            Please select an executed backtest run from the dropdown menu to inspect transaction history logs.
          </p>
        </div>
      ) : (
        <div className="bg-card border border-border rounded-xl overflow-hidden animate-fade-in">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-border bg-slate-950/20 text-slate-500 uppercase tracking-wider text-[10px] font-mono">
                  <th className="py-3 px-4">Ticker</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Contracts</th>
                  <th className="py-3 px-4">Entry Details</th>
                  <th className="py-3 px-4">Exit Details</th>
                  <th className="py-3 px-4">Realized P&L</th>
                  <th className="py-3 px-4">Confidence</th>
                  <th className="py-3 px-4 text-right">Reasoning Log</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {singleRunDetails.trades
                  ?.filter(t => {
                    const matchTicker = t.ticker.toLowerCase().includes(ledgerFilter.toLowerCase());
                    const matchAction = ledgerActionFilter === 'ALL' || t.decision === ledgerActionFilter;
                    return matchTicker && matchAction;
                  })
                  .map((trade, idx) => {
                    const isPositivePnl = trade.pnl > 0;
                    const isNegativePnl = trade.pnl < 0;
                    return (
                      <tr key={idx} className="hover:bg-slate-800/40 transition-all">
                        <td className="py-3 px-4 font-bold text-slate-300 font-mono">{trade.ticker}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                              trade.decision === 'LONG' || trade.decision === 'BUY'
                                ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                : trade.decision === 'SHORT' || trade.decision === 'SELL'
                                ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                            }`}
                          >
                            {trade.decision}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-400">{trade.quantity ? trade.quantity.toLocaleString() : '-'}</td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          <div>{trade.entry_price ? formatCurrency(trade.entry_price) : (trade.price ? formatCurrency(trade.price) : '-')}</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">{trade.entry_date || '-'}</div>
                        </td>
                        <td className="py-3 px-4 font-mono text-slate-300">
                          <div>{trade.exit_price ? formatCurrency(trade.exit_price) : '-'}</div>
                          <div className="text-[10px] text-slate-500 mt-0.5">{trade.exit_date || '-'}</div>
                        </td>
                        <td className={`py-3 px-4 font-mono font-bold ${
                          isPositivePnl ? 'text-emerald-400' : isNegativePnl ? 'text-rose-400' : 'text-slate-300'
                        }`}>
                          {trade.pnl !== undefined ? (isPositivePnl ? '+' : '') + formatCurrency(trade.pnl) : '-'}
                        </td>
                        <td className="py-3 px-4 font-mono">
                          <div className="flex items-center gap-1.5">
                            <div className="w-12 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                              <div
                                className="bg-blue-500 h-1.5 rounded-full"
                                style={{ width: `${trade.confidence}%` }}
                              ></div>
                            </div>
                            <span className="text-[10px] text-slate-400">{trade.confidence}%</span>
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => setSelectedTrade(trade)}
                            className="bg-slate-900 border border-border hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-all font-semibold px-2.5 py-1 rounded"
                          >
                            Inspect Log
                          </button>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Ledger detail reasoning inspection Modal */}
      {selectedTrade && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fade-in">
          <div className="bg-card border border-border rounded-xl max-w-lg w-full overflow-hidden shadow-2xl">
            <div className="h-14 bg-slate-950/80 border-b border-border px-6 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-1.5 py-0.5 border border-blue-500/20 rounded font-mono">
                  {selectedTrade.ticker}
                </span>
                <span className="text-xs font-bold text-slate-300">LLM Reasoning Log</span>
              </div>
              <button
                onClick={() => setSelectedTrade(null)}
                className="text-slate-500 hover:text-slate-200 transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4 text-center">
                <div className="bg-slate-950/40 p-3 rounded border border-border/50">
                  <div className="text-[9px] text-slate-500 uppercase tracking-wider font-bold">Signal Decision</div>
                  <div className={`text-sm font-black mt-1 uppercase ${
                    selectedTrade.decision === 'BUY' ? 'text-emerald-400' : selectedTrade.decision === 'SELL' ? 'text-rose-400' : 'text-amber-400'
                  }`}>
                    {selectedTrade.decision}
                  </div>
                </div>
                <div className="bg-slate-950/40 p-3 rounded border border-border/50">
                  <div className="text-[9px] text-slate-500 uppercase tracking-wider font-bold">Signal Confidence</div>
                  <div className="text-sm font-black text-slate-300 mt-1 font-mono">
                    {selectedTrade.confidence}%
                  </div>
                </div>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-2">Reasoning Rationale</span>
                <div className="p-4 bg-slate-950 border border-border rounded-lg text-xs leading-relaxed text-slate-400 h-44 overflow-y-auto font-mono">
                  {selectedTrade.reasoning || "No reasoning details returned by agent response."}
                </div>
              </div>
            </div>

            <div className="h-14 bg-slate-950/40 border-t border-border px-6 flex justify-end items-center">
              <button
                onClick={() => setSelectedTrade(null)}
                className="bg-blue-600 hover:bg-blue-500 text-slate-100 font-bold px-4 py-2 rounded text-xs transition-colors"
              >
                Dismiss Log
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
