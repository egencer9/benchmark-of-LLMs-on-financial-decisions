import React from 'react';
import { DollarSign } from 'lucide-react';

export default function MarketNews({
  exchange,
  marketData,
  loadingMarket,
  newsData,
  loadingNews,
  formatCurrency
}) {
  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header info */}
      <div className="bg-card border border-border p-6 rounded-xl flex items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <DollarSign className="h-5 w-5 text-blue-500" />
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Exchange Constituents Prices & Scraped News Feed</h3>
            <p className="text-[10px] text-slate-500 mt-0.5">Explore active exchange stocks list, prices, and latest news count.</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Stocks grid */}
        <div className="lg:col-span-1 bg-card border border-border p-6 rounded-xl h-[500px] flex flex-col">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center justify-between">
            <span>Constituents List</span>
            {marketData?.latest_date && (
              <span className="text-[10px] font-mono text-slate-500 normal-case">Latest Data: {marketData.latest_date}</span>
            )}
          </h3>

          {loadingMarket ? (
            <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
              Loading prices cache...
            </div>
          ) : !marketData || !marketData.tickers ? (
            <div className="flex-1 flex items-center justify-center text-xs text-slate-500 text-center px-4">
              No market data CSV found. Ensure you execute a data scrape script first.
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {marketData.tickers.map(stock => (
                <div key={stock.ticker} className="flex justify-between items-center p-2.5 rounded bg-slate-950/40 border border-border/40 hover:border-slate-800 transition-all font-mono">
                  <div className="truncate pr-2">
                    <div className="font-bold text-slate-200 text-xs truncate">{stock.ticker}</div>
                    <div className="text-[9px] text-slate-500 truncate mt-0.5">{stock.company_name}</div>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-xs font-bold text-slate-300">{formatCurrency(stock.price)}</div>
                    <div className="text-[9px] text-slate-500 mt-0.5">{stock.news_count} articles</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* News list */}
        <div className="lg:col-span-2 bg-card border border-border p-6 rounded-xl h-[500px] flex flex-col">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Latest Financial News Timeline</h3>

          {loadingNews ? (
            <div className="flex-1 flex items-center justify-center text-xs text-slate-500">
              Loading news feed...
            </div>
          ) : newsData.length === 0 ? (
            <div className="flex-1 flex items-center justify-center text-xs text-slate-500 text-center px-4">
              No scraped articles found in local news database.
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {newsData.map((news, idx) => (
                <div key={idx} className="p-4 rounded bg-slate-950/40 border border-border/40 hover:bg-slate-950/70 transition-all">
                  <div className="flex justify-between items-center mb-1.5">
                    <span className="text-[10px] font-bold text-blue-400 font-mono bg-blue-500/10 px-1.5 py-0.5 border border-blue-500/20 rounded">
                      {news.ticker}
                    </span>
                    <div className="flex items-center gap-3 text-[9px] text-slate-500 font-mono font-bold">
                      <span>{news.source}</span>
                      <span>•</span>
                      <span>{news.publishedAt}</span>
                    </div>
                  </div>
                  <h4 className="text-xs font-bold text-slate-200 hover:text-blue-400 transition-colors leading-relaxed cursor-default">
                    {news.title}
                  </h4>
                  <p className="text-[11px] text-slate-500 mt-1.5 leading-relaxed truncate-2-lines">
                    {news.description}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
