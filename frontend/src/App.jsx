import React, { useState, useEffect, useRef } from 'react';
import {
  TrendingUp,
  Cpu,
  BookOpen,
  DollarSign,
  Activity,
  Key,
  Play,
  RotateCcw,
  AlertTriangle,
  FolderOpen,
  Eye,
  EyeOff,
  Percent,
  Search,
  Sliders,
  ChevronRight,
  TrendingDown,
  X,
  Layers
} from 'lucide-react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  PieChart,
  Pie,
  Cell
} from 'recharts';

export default function App() {
  // Navigation & Tab States
  const [exchange, setExchange] = useState('BIST30'); // "BIST30" or "NASDAQ"
  const [subTab, setSubTab] = useState('dashboard'); // "dashboard", "insights", "ledger", "market", "runner"

  // Config and Data States
  const [configData, setConfigData] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [newsData, setNewsData] = useState([]);
  const [historyList, setHistoryList] = useState([]);
  const [selectedRunsForCompare, setSelectedRunsForCompare] = useState([]);
  const [compareData, setCompareData] = useState([]);
  const [singleRunDetails, setSingleRunDetails] = useState(null);
  const [selectedHistoryFile, setSelectedHistoryFile] = useState('');

  // Runner Parameters State
  const [selectedModelIndex, setSelectedModelIndex] = useState(0);
  const [devModeOverride, setDevModeOverride] = useState(true);
  const [startDateInput, setStartDateInput] = useState('');
  const [endDateInput, setEndDateInput] = useState('');
  const [initialCashInput, setInitialCashInput] = useState(1000000);

  // Global Runner / WS States
  const [runnerStatus, setRunnerStatus] = useState('idle'); // "idle", "running", "finished", "failed"
  const [runnerModel, setRunnerModel] = useState(null);
  const [runnerExchange, setRunnerExchange] = useState(null);
  const [runnerProgress, setRunnerProgress] = useState({ current_day: 0, total_days: 0, percent: 0.0 });
  const [runnerLogs, setRunnerLogs] = useState([]);
  const [runnerExitCode, setRunnerExitCode] = useState(null);

  // WS Connection States
  const [wsConnected, setWsConnected] = useState(false);
  const [wsError, setWsError] = useState(null);

  // UI Widget States
  const [showKeys, setShowKeys] = useState(false);
  const [selectedTrade, setSelectedTrade] = useState(null); // reasoning modal target
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [ledgerFilter, setLedgerFilter] = useState('');
  const [ledgerActionFilter, setLedgerActionFilter] = useState('ALL');
  
  // Loading & Error States
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [loadingMarket, setLoadingMarket] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingCompare, setLoadingCompare] = useState(false);
  const [loadingNews, setLoadingNews] = useState(false);
  const [apiError, setApiError] = useState(null);

  const wsRef = useRef(null);
  const logsEndRef = useRef(null);

  const currencySymbol = exchange === 'BIST30' ? '₺' : '$';
  const currencyCode = exchange === 'BIST30' ? 'TRY' : 'USD';

  // WebSocket Connection Setup with Reconnect
  useEffect(() => {
    let reconnectTimer;
    const connectWS = () => {
      console.log("Connecting to WebSocket...");
      const ws = new WebSocket("ws://localhost:8000/api/backtest/stream");
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("WebSocket connection established");
        setWsConnected(true);
        setWsError(null);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "init") {
            setRunnerStatus(data.status);
            setRunnerModel(data.active_model);
            setRunnerExchange(data.active_exchange);
            setRunnerProgress(data.progress);
            setRunnerLogs(data.logs || []);
          } else if (data.type === "log") {
            setRunnerLogs(prev => [...prev, data.message]);
            if (data.progress) {
              setRunnerProgress(data.progress);
            }
          } else if (data.type === "exit") {
            setRunnerStatus(data.status);
            setRunnerExitCode(data.code);
            fetchHistory(); // Refresh history list
          }
        } catch (err) {
          console.error("Error parsing WS frame: ", err);
        }
      };

      ws.onerror = (err) => {
        console.error("WebSocket error: ", err);
        setWsError("WebSocket connection failed. Attempting to reconnect...");
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
        setWsConnected(false);
        reconnectTimer = setTimeout(connectWS, 5000);
      };
    };

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
      clearTimeout(reconnectTimer);
    };
  }, [exchange]);

  // Auto-scroll log console
  useEffect(() => {
    if (logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [runnerLogs]);

  // Load configuration on mount
  useEffect(() => {
    fetchConfig();
  }, []);

  // Fetch exchange specific details when tab changes
  useEffect(() => {
    fetchMarketData();
    fetchHistory();
    fetchNews();
    setCompareData([]);
    setSelectedRunsForCompare([]);
    setSingleRunDetails(null);
    setSelectedHistoryFile('');
  }, [exchange]);

  // Handle run selection comparison fetches
  useEffect(() => {
    if (selectedRunsForCompare.length === 0) {
      setCompareData([]);
      return;
    }
    fetchComparison();
  }, [selectedRunsForCompare]);

  // Fetch API handlers
  const fetchConfig = async () => {
    setLoadingConfig(true);
    try {
      const res = await fetch("http://localhost:8000/api/config");
      if (!res.ok) throw new Error("Failed to load config.");
      const data = await res.json();
      setConfigData(data);
      setDevModeOverride(data.dev_mode);
      setApiError(null);
    } catch (err) {
      setApiError(err.message);
    } finally {
      setLoadingConfig(false);
    }
  };

  const fetchMarketData = async () => {
    setLoadingMarket(true);
    try {
      const res = await fetch(`http://localhost:8000/api/market-data?exchange=${exchange}`);
      if (!res.ok) throw new Error(`Failed to load ${exchange} market data.`);
      const data = await res.json();
      setMarketData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingMarket(false);
    }
  };

  const fetchNews = async () => {
    setLoadingNews(true);
    try {
      const res = await fetch(`http://localhost:8000/api/news?exchange=${exchange}&limit=25`);
      if (!res.ok) throw new Error("Failed to fetch news.");
      const data = await res.json();
      setNewsData(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingNews(false);
    }
  };

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const res = await fetch(`http://localhost:8000/api/backtest/history?exchange=${exchange}&page=${historyPage}&limit=20`);
      if (!res.ok) throw new Error("Failed to fetch history list.");
      const data = await res.json();
      setHistoryList(data.runs || []);
      setHistoryTotal(data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchComparison = async () => {
    setLoadingCompare(true);
    try {
      const runsParam = selectedRunsForCompare.join(',');
      const res = await fetch(`http://localhost:8000/api/results/compare?exchange=${exchange}&runs=${runsParam}`);
      if (!res.ok) throw new Error("Failed to compare runs.");
      const runs = await res.json();

      // Format data for Recharts overlay
      // We align by step index (day index)
      const maxLength = Math.max(...runs.map(r => r.history.length));
      const chartPoints = [];

      for (let i = 0; i < maxLength; i++) {
        const point = { day: i + 1 };
        runs.forEach(run => {
          // If we have detailed history, retrieve calendar dates
          const detail = run.detailed_history && run.detailed_history[i];
          if (detail && detail.date) {
            point.date = detail.date;
          }
          point[run.alias] = run.history[i] !== undefined ? run.history[i] : null;
        });
        chartPoints.push(point);
      }
      setCompareData(chartPoints);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCompare(false);
    }
  };

  const loadRunDetails = async (filename) => {
    setSelectedHistoryFile(filename);
    try {
      const res = await fetch(`http://localhost:8000/api/results/${exchange}/${filename}`);
      if (!res.ok) throw new Error("Failed to load run details.");
      const data = await res.json();
      setSingleRunDetails(data);
    } catch (err) {
      console.error(err);
    }
  };

  const startBacktest = async () => {
    if (runnerStatus === 'running') return;
    try {
      const res = await fetch("http://localhost:8000/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_index: selectedModelIndex,
          exchange: exchange,
          dev_mode: devModeOverride,
          start_date: startDateInput || null,
          end_date: endDateInput || null,
          cash: parseFloat(initialCashInput) || 1000000
        })
      });

      if (res.status === 409) {
        alert("A backtest is already running. You must wait for it to complete.");
        return;
      }
      if (!res.ok) throw new Error("Trigger failed.");
      
      setRunnerStatus('running');
      setRunnerLogs([]);
      setRunnerExitCode(null);
    } catch (err) {
      alert(`Failed to start backtest: ${err.message}`);
    }
  };

  const cancelBacktest = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send("cancel");
    }
  };

  // Helper selectors
  const toggleCompareRun = (filename) => {
    setSelectedRunsForCompare(prev => {
      if (prev.includes(filename)) {
        return prev.filter(f => f !== filename);
      } else {
        // Limit to 3 compare runs overlay
        if (prev.length >= 3) {
          alert("You can compare up to 3 runs at the same time.");
          return prev;
        }
        return [...prev, filename];
      }
    });
  };

  // Format currency
  const formatCurrency = (val) => {
    if (val === undefined || val === null) return '-';
    return `${currencySymbol}${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Allocation donut data helper (from latest day of active run details)
  const getAllocationData = () => {
    if (!singleRunDetails || !singleRunDetails.detailed_history) return [];
    const latestDay = singleRunDetails.detailed_history[singleRunDetails.detailed_history.length - 1];
    if (!latestDay) return [];

    const data = [{ name: 'Cash', value: latestDay.cash }];
    let stocksValue = 0;
    
    // Sum stock holdings values using latest day details if available
    // For simplicity, we calculate total_value - cash
    stocksValue = latestDay.total_value - latestDay.cash;
    if (stocksValue > 0) {
      data.push({ name: 'Stock Holdings', value: stocksValue });
    }
    return data;
  };

  const COLORS = ['#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6'];

  return (
    <div className="flex h-screen bg-background text-slate-100 font-sans select-none flex-col">
      {/* 1. Persistent Top DEV_MODE Banner */}
      {configData?.dev_mode && (
        <div className="bg-amber-600/90 text-background px-4 py-1 text-center text-xs font-bold flex items-center justify-center gap-2 border-b border-amber-500/20 shrink-0">
          <AlertTriangle className="h-4 w-4" />
          <span>⚠ DEV MODE ACTIVE — Dummy actions are being simulated (No LLM API costs)</span>
        </div>
      )}

      {/* Main Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* 2. Sidebar */}
        <aside className="w-64 bg-card border-r border-border flex flex-col justify-between shrink-0">
          <div>
            {/* Brand Title */}
            <div className="h-16 flex items-center px-6 border-b border-border gap-3">
              <div className="p-2 bg-blue-600/20 text-blue-500 rounded-lg">
                <Cpu className="h-5 w-5" />
              </div>
              <div>
                <h1 className="font-extrabold text-sm tracking-wider uppercase bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent">
                  LLM BENCHMARK
                </h1>
                <span className="text-[10px] text-slate-500 block">NASDAQ / BIST30 BENCHMARK</span>
              </div>
            </div>

            {/* API Keys Widget (Reveal Toggle) */}
            <div className="p-4 border-b border-border bg-slate-950/40">
              <button
                onClick={() => setShowKeys(!showKeys)}
                className="w-full flex items-center justify-between text-[11px] font-bold text-slate-400 hover:text-slate-200 transition-colors uppercase tracking-wider mb-2"
              >
                <span className="flex items-center gap-1.5">
                  <Key className="h-3.5 w-3.5" /> Configure API Keys
                </span>
                {showKeys ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
              </button>

              {showKeys && configData?.api_keys && (
                <div className="space-y-1.5 text-[10px] bg-black/40 p-2 rounded border border-white/5 font-mono">
                  {Object.entries(configData.api_keys).map(([key, val]) => (
                    <div key={key} className="flex flex-col">
                      <span className="text-slate-500 text-[9px]">{key}</span>
                      <span className="text-slate-300 font-bold truncate">{val}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Exchange Scope Selector */}
            <div className="p-4 border-b border-border">
              <label className="text-[10px] font-bold text-slate-500 block uppercase tracking-wider mb-2">Active Exchange</label>
              <div className="grid grid-cols-2 gap-2 bg-slate-950 p-1 rounded-lg border border-border">
                <button
                  onClick={() => setExchange('BIST30')}
                  className={`py-1.5 rounded-md text-xs font-bold transition-all ${
                    exchange === 'BIST30'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                  }`}
                >
                  BIST30 (TRY)
                </button>
                <button
                  onClick={() => setExchange('NASDAQ')}
                  className={`py-1.5 rounded-md text-xs font-bold transition-all ${
                    exchange === 'NASDAQ'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                  }`}
                >
                  NASDAQ (USD)
                </button>
              </div>
            </div>

            {/* Sidebar Navigation */}
            <nav className="p-4 space-y-1">
              <button
                onClick={() => setSubTab('dashboard')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  subTab === 'dashboard'
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <TrendingUp className="h-4 w-4" />
                <span>Dashboard Overview</span>
              </button>

              <button
                onClick={() => setSubTab('insights')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  subTab === 'insights'
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <Layers className="h-4 w-4" />
                <span>Model Insights</span>
              </button>

              <button
                onClick={() => setSubTab('ledger')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  subTab === 'ledger'
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <BookOpen className="h-4 w-4" />
                <span>Trade Ledger</span>
              </button>

              <button
                onClick={() => setSubTab('market')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  subTab === 'market'
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <DollarSign className="h-4 w-4" />
                <span>Market & News</span>
              </button>

              <button
                onClick={() => setSubTab('runner')}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                  subTab === 'runner'
                    ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                }`}
              >
                <Play className="h-4 w-4" />
                <span>Backtest Runner</span>
              </button>
            </nav>
          </div>

          {/* 3. Global Run Status Indicator (Sidebar Footer) */}
          <div className="p-4 bg-slate-950/60 border-t border-border">
            {runnerStatus === 'running' ? (
              <div
                onClick={() => setSubTab('runner')}
                className="cursor-pointer bg-blue-950/40 border border-blue-500/20 p-3 rounded-lg hover:bg-blue-950/60 transition-all"
              >
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider">Running Simulation</span>
                </div>
                <div className="text-[11px] font-bold truncate text-slate-400">{runnerModel}</div>
                <div className="text-[9px] text-slate-500 uppercase tracking-wider mb-2">{runnerExchange}</div>
                
                {/* Progress bar */}
                <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${runnerProgress.percent}%` }}
                  ></div>
                </div>
                <div className="flex justify-between items-center text-[9px] text-slate-500 font-bold font-mono mt-1">
                  <span>Day {runnerProgress.current_day}/{runnerProgress.total_days}</span>
                  <span>{runnerProgress.percent}%</span>
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2 px-2 py-1">
                <span className="h-2 w-2 rounded-full bg-slate-700"></span>
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Simulation Engine Idle</span>
              </div>
            )}

            {/* WS Status Badge */}
            <div className="flex justify-between items-center text-[9px] text-slate-600 font-mono mt-3 px-2 border-t border-border/40 pt-2">
              <span>WebSocket status:</span>
              <span className={wsConnected ? 'text-emerald-500 font-bold' : 'text-rose-500 font-bold'}>
                {wsConnected ? 'CONNECTED' : 'DISCONNECTED'}
              </span>
            </div>
            {wsError && (
              <div className="text-[8px] text-rose-500 font-semibold px-2 mt-1.5 truncate">
                {wsError}
              </div>
            )}
          </div>
        </aside>

        {/* 4. Main Content Area */}
        <main className="flex-1 bg-background flex flex-col overflow-hidden">
          {/* Header */}
          <header className="h-16 border-b border-border px-8 flex items-center justify-between shrink-0 bg-card/20">
            <div className="flex items-center gap-3">
              <span className="text-[10px] font-bold text-blue-500 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20 uppercase font-mono">
                {exchange} Mode
              </span>
              <ChevronRight className="h-4 w-4 text-slate-600" />
              <span className="text-sm font-semibold capitalize text-slate-200">
                {subTab === 'ledger' ? 'Trade Transaction Ledger' : subTab === 'market' ? 'Market Data & RSS Explorer' : subTab === 'insights' ? 'Model Portfolio Insights' : subTab}
              </span>
            </div>

            <div className="flex items-center gap-4 text-xs">
              <span className="text-slate-500 font-mono">Currency:</span>
              <span className="text-slate-300 font-extrabold bg-slate-900 border border-border px-2.5 py-1 rounded">
                {currencyCode} ({currencySymbol})
              </span>
            </div>
          </header>

          {/* Sub-tab view components */}
          <div className="flex-1 overflow-y-auto p-8">
            {apiError && (
              <div className="mb-6 p-4 bg-rose-950/30 border border-rose-500/20 text-rose-400 rounded-lg text-xs flex justify-between items-center animate-fade-in">
                <span>{apiError}</span>
                <button onClick={fetchConfig} className="bg-rose-500 text-slate-950 font-bold px-3 py-1 rounded hover:bg-rose-400 transition-colors">
                  Retry Connection
                </button>
              </div>
            )}

            {/* TAB 1: DASHBOARD OVERVIEW */}
            {subTab === 'dashboard' && (
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
                      <p className="text-[11px] text-slate-500 mt-1">Select runs in the right drawer to overlay and evaluate cumulative return curves.</p>
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
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                          <XAxis
                            dataKey="date"
                            stroke="#475569"
                            tickFormatter={(v) => v || ''}
                          />
                          <YAxis
                            stroke="#475569"
                            tickFormatter={(v) => formatCurrency(v)}
                          />
                          <Tooltip
                            contentStyle={{ backgroundColor: '#0f111a', border: '1px solid #1e293b' }}
                            formatter={(value) => [formatCurrency(value), "Portfolio Value"]}
                          />
                          <Legend />
                          {selectedRunsForCompare.map((fname, idx) => {
                            const runMeta = historyList.find(h => h.filename === fname);
                            const label = runMeta ? runMeta.alias : fname;
                            return (
                              <Line
                                key={fname}
                                type="monotone"
                                dataKey={label}
                                stroke={COLORS[idx % COLORS.length]}
                                strokeWidth={2}
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
                        Select one or more historical benchmark runs from the checklist on the right to visualize comparative portfolio performance.
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
                            <tr className="border-b border-border text-slate-500 uppercase tracking-wider text-[10px]">
                              <th className="py-2.5 px-3">Compare</th>
                              <th className="py-2.5 px-3">Model Alias</th>
                              <th className="py-2.5 px-3">Timestamp</th>
                              <th className="py-2.5 px-3">Cum. Return</th>
                              <th className="py-2.5 px-3">Max DD</th>
                              <th className="py-2.5 px-3 text-right">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-border/60">
                            {historyList.map(run => (
                              <tr key={run.filename} className="hover:bg-white/5 transition-all">
                                <td className="py-3 px-3">
                                  <input
                                    type="checkbox"
                                    checked={selectedRunsForCompare.includes(run.filename)}
                                    onChange={() => toggleCompareRun(run.filename)}
                                    className="h-4 w-4 bg-slate-900 border-border rounded text-blue-600 accent-blue-600 cursor-pointer"
                                  />
                                </td>
                                <td className="py-3 px-3 font-bold text-slate-300">{run.alias}</td>
                                <td className="py-3 px-3 text-slate-500 font-mono">{run.timestamp}</td>
                                <td className="py-3 px-3 text-emerald-400 font-bold font-mono">{run.metrics?.["Cumulative Return"] || '0.00%'}</td>
                                <td className="py-3 px-3 text-rose-400 font-mono">{run.metrics?.["Max Drawdown"] || '0.00%'}</td>
                                <td className="py-3 px-3 text-right">
                                  <button
                                    onClick={() => {
                                      loadRunDetails(run.filename);
                                      setSubTab('insights');
                                    }}
                                    className="bg-slate-800 border border-slate-700 text-slate-300 font-semibold px-2.5 py-1 rounded hover:bg-slate-700 transition-colors"
                                  >
                                    View Details
                                  </button>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  {/* Right comparison metrics cards */}
                  <div className="bg-card border border-border p-6 rounded-xl">
                    <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Direct Run Metrics Diffs</h3>
                    
                    {selectedRunsForCompare.length < 2 ? (
                      <div className="h-64 flex flex-col justify-center items-center text-center text-xs text-slate-500 border border-dashed border-border rounded">
                        <Sliders className="h-6 w-6 text-slate-600 mb-2" />
                        <span>Select 2 runs to compare metrics side-by-side</span>
                      </div>
                    ) : (
                      <div className="space-y-4">
                        {selectedRunsForCompare.map((fname, idx) => {
                          const run = historyList.find(h => h.filename === fname);
                          if (!run) return null;
                          return (
                            <div key={fname} className="p-4 rounded-lg bg-slate-950/60 border border-border animate-fade-in">
                              <div className="flex items-center gap-2 mb-2">
                                <div className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
                                <span className="font-bold text-xs truncate text-slate-200">{run.alias}</span>
                              </div>
                              
                              <div className="grid grid-cols-3 gap-2 text-center mt-2 pt-2 border-t border-white/5">
                                <div>
                                  <div className="text-[9px] text-slate-500 uppercase tracking-wider">Return</div>
                                  <div className="text-xs font-bold text-emerald-400 font-mono mt-0.5">{run.metrics?.["Cumulative Return"]}</div>
                                </div>
                                <div>
                                  <div className="text-[9px] text-slate-500 uppercase tracking-wider">Max DD</div>
                                  <div className="text-xs font-bold text-rose-400 font-mono mt-0.5">{run.metrics?.["Max Drawdown"]}</div>
                                </div>
                                <div>
                                  <div className="text-[9px] text-slate-500 uppercase tracking-wider">Sortino</div>
                                  <div className="text-xs font-bold text-amber-500 font-mono mt-0.5">{run.metrics?.["Sortino Ratio"]}</div>
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
            )}

            {/* TAB 2: MODEL PORTFOLIO INSIGHTS */}
            {subTab === 'insights' && (
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
                              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
                              <XAxis dataKey="date" stroke="#475569" />
                              <YAxis stroke="#475569" tickFormatter={(v) => formatCurrency(v)} />
                              <Tooltip
                                contentStyle={{ backgroundColor: '#0f111a', border: '1px solid #1e293b' }}
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
                              <Tooltip formatter={(value) => formatCurrency(value)} />
                              <Legend />
                            </PieChart>
                          </ResponsiveContainer>
                        </div>
                      </div>

                      {/* Ticker holdings list table */}
                      <div className="bg-card border border-border p-6 rounded-xl">
                        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Stock Holdings Ledger</h3>
                        
                        <div className="space-y-3 font-mono text-xs">
                          {Object.entries(singleRunDetails.detailed_history?.[singleRunDetails.detailed_history.length - 1]?.holdings || {}).length === 0 ? (
                            <div className="text-center py-6 text-slate-500 text-[11px]">
                              Zero active stock holdings (100% Cash allocation).
                            </div>
                          ) : (
                            Object.entries(singleRunDetails.detailed_history[singleRunDetails.detailed_history.length - 1].holdings).map(([ticker, shares], idx) => (
                              <div key={ticker} className="flex justify-between items-center p-2.5 rounded bg-slate-950/40 border border-border/40">
                                <div>
                                  <div className="font-bold text-slate-200 text-xs">{ticker}</div>
                                  <div className="text-[10px] text-slate-500 mt-0.5">{shares.toLocaleString()} Shares</div>
                                </div>
                                <div className="text-slate-400 text-xs font-bold">
                                  {/* Current price lookup if present in marketData */}
                                  {marketData?.tickers?.find(t => t.ticker === ticker) ? (
                                    <span>
                                      {formatCurrency(shares * (marketData.tickers.find(t => t.ticker === ticker)?.price || 0))}
                                    </span>
                                  ) : (
                                    <span className="text-[10px] text-slate-500">Value pending...</span>
                                  )}
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 3: TRADE LEDGER */}
            {subTab === 'ledger' && (
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
                      <option value="BUY">BUY Only</option>
                      <option value="SELL">SELL Only</option>
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
                            <th className="py-3 px-4">Action</th>
                            <th className="py-3 px-4">Price</th>
                            <th className="py-3 px-4">Quantity</th>
                            <th className="py-3 px-4">Value</th>
                            <th className="py-3 px-4">Confidence</th>
                            <th className="py-3 px-4 text-right">Reasoning</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-border/60">
                          {singleRunDetails.trades
                            ?.filter(t => {
                              const matchTicker = t.ticker.toLowerCase().includes(ledgerFilter.toLowerCase());
                              const matchAction = ledgerActionFilter === 'ALL' || t.decision === ledgerActionFilter;
                              return matchTicker && matchAction;
                            })
                            .map((trade, idx) => (
                              <tr key={idx} className="hover:bg-white/5 transition-all">
                                <td className="py-3 px-4 font-bold text-slate-300 font-mono">{trade.ticker}</td>
                                <td className="py-3 px-4">
                                  <span
                                    className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                      trade.decision === 'BUY'
                                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                        : trade.decision === 'SELL'
                                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                    }`}
                                  >
                                    {trade.decision}
                                  </span>
                                </td>
                                <td className="py-3 px-4 font-mono text-slate-300">{formatCurrency(trade.price)}</td>
                                <td className="py-3 px-4 font-mono text-slate-400">{trade.quantity ? trade.quantity.toLocaleString() : '-'}</td>
                                <td className="py-3 px-4 font-mono text-slate-300 font-semibold">{trade.value ? formatCurrency(trade.value) : '-'}</td>
                                <td className="py-3 px-4 font-mono">
                                  <div className="flex items-center gap-1.5">
                                    <div className="w-12 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                                      <div
                                        className="bg-blue-500 h-1.5 rounded-full"
                                        style={{ width: `${trade.confidence * 100}%` }}
                                      ></div>
                                    </div>
                                    <span className="text-[10px] text-slate-400">{(trade.confidence * 100).toFixed(0)}%</span>
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
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 4: MARKET & NEWS */}
            {subTab === 'market' && (
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
                        <span className="text-[10px] font-mono text-slate-500 lowercase normal-case">Latest Data: {marketData.latest_date}</span>
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
            )}

            {/* TAB 5: BACKTEST RUNNER */}
            {subTab === 'runner' && (
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

                      {/* Date ranges */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="text-[10px] text-slate-500 uppercase tracking-wider font-bold block mb-2">Start Date</label>
                          <input
                            type="text"
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
                            type="text"
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
                        <input
                          type="number"
                          value={initialCashInput}
                          onChange={(e) => setInitialCashInput(e.target.value)}
                          disabled={runnerStatus === 'running'}
                          className="w-full bg-slate-950 border border-border rounded-lg text-xs font-bold text-slate-200 px-4 py-2.5 outline-none font-mono disabled:cursor-not-allowed disabled:opacity-50"
                        />
                      </div>

                      {/* Dev mode toggle */}
                      <div className="flex items-center justify-between p-3 rounded-lg bg-slate-950 border border-border">
                        <div>
                          <span className="text-[10px] text-slate-400 font-bold block">DEV MODE (Simulated Decisions)</span>
                          <span className="text-[9px] text-slate-500 block mt-0.5">Toggle to prevent Gemini/OpenRouter API key usage costs</span>
                        </div>
                        <input
                          type="checkbox"
                          checked={devModeOverride}
                          onChange={(e) => setDevModeOverride(e.target.checked)}
                          disabled={runnerStatus === 'running'}
                          className="h-5 w-5 bg-slate-900 border-border rounded text-blue-600 accent-blue-600 cursor-pointer disabled:cursor-not-allowed"
                        />
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
                    <div className="flex-1 bg-black/60 border border-border rounded-lg p-4 font-mono text-xs overflow-y-auto text-slate-400 flex flex-col space-y-1.5 relative">
                      {runnerLogs.length === 0 ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-center text-slate-600 text-xs px-8">
                          <Cpu className="h-8 w-8 text-slate-700 mb-2" />
                          <span>Simulation Log terminal is empty. Trigger a run to steam output logs.</span>
                        </div>
                      ) : (
                        runnerLogs.map((logLine, idx) => (
                          <div key={idx} className="whitespace-pre-wrap leading-relaxed truncate">
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
            )}
          </div>
        </main>
      </div>

      {/* 5. Ledger detail reasoning inspection Modal */}
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
                    {(selectedTrade.confidence * 100).toFixed(0)}%
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
