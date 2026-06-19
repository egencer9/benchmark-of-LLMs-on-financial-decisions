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
  Layers,
  Sun,
  Moon,
  Database,
  Trash2
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

import DashboardOverview from './components/DashboardOverview';
import ModelInsights from './components/ModelInsights';
import TradeLedger from './components/TradeLedger';
import MarketNews from './components/MarketNews';
import BacktestRunner from './components/BacktestRunner';

export default function App() {
  const hostName = window.location.hostname || 'localhost';
  const API_BASE = `http://${hostName}:8000`;
  const WS_BASE = `ws://${hostName}:8000`;

  // Navigation & Tab States
  const [exchange, setExchange] = useState('NASDAQ'); // "BIST30" or "NASDAQ"
  const [subTab, setSubTab] = useState('dashboard'); // "dashboard", "insights", "ledger", "market", "runner"
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark');

  // Config and Data States
  const [configData, setConfigData] = useState(null);
  const [marketData, setMarketData] = useState(null);
  const [newsData, setNewsData] = useState([]);
  const [historyList, setHistoryList] = useState([]);
  const [selectedRunsForCompare, setSelectedRunsForCompare] = useState([]);
  const [selectedRunMeta, setSelectedRunMeta] = useState({});
  const [compareData, setCompareData] = useState([]);
  const [singleRunDetails, setSingleRunDetails] = useState(null);
  const [selectedHistoryFile, setSelectedHistoryFile] = useState('');

  // Runner Parameters State
  const [selectedModelIndex, setSelectedModelIndex] = useState(0);
  const [startDateInput, setStartDateInput] = useState('');
  const [endDateInput, setEndDateInput] = useState('');
  const [initialCashInput, setInitialCashInput] = useState(100000);
  const [tradingApproach, setTradingApproach] = useState('Balanced');

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

  // Cache Status State
  const [cacheStatus, setCacheStatus] = useState(null);
  const [loadingCache, setLoadingCache] = useState(false);

  const wsRef = useRef(null);
  const fetchHistoryRef = useRef(null);

  const currencySymbol = exchange === 'BIST30' ? '₺' : '$';
  const currencyCode = exchange === 'BIST30' ? 'TRY' : 'USD';

  // WebSocket Connection Setup with Reconnect
  useEffect(() => {
    let reconnectTimer;
    const connectWS = () => {
      console.log("Connecting to WebSocket...");
      const ws = new WebSocket(`${WS_BASE}/api/backtest/stream`);
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
            fetchHistoryRef.current?.(); // Refresh history list
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
  }, []);

  // Load configuration on mount
  useEffect(() => {
    fetchConfig();
  }, []);

  // Update theme class on HTML element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Fetch exchange specific details when tab changes
  useEffect(() => {
    fetchMarketData();
    fetchNews();
    fetchCacheStatus();
    setCompareData([]);
    setSelectedRunsForCompare([]);
    setSelectedRunMeta({});
    setSingleRunDetails(null);
    setSelectedHistoryFile('');
    
    if (historyPage === 1) {
      fetchHistory();
    } else {
      setHistoryPage(1);
    }
  }, [exchange]);

  // Fetch history list when page changes
  useEffect(() => {
    fetchHistory();
  }, [historyPage]);


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
      const res = await fetch(`${API_BASE}/api/config`);
      if (!res.ok) throw new Error("Failed to load config.");
      const data = await res.json();
      setConfigData(data);
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
      const res = await fetch(`${API_BASE}/api/market-data?exchange=${exchange}`);
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
      const res = await fetch(`${API_BASE}/api/news?exchange=${exchange}&limit=25`);
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
      const res = await fetch(`${API_BASE}/api/backtest/history?exchange=${exchange}&page=${historyPage}&limit=20`);
      if (!res.ok) throw new Error("Failed to fetch history list.");
      const data = await res.json();
      const runs = data.runs || [];
      setHistoryList(runs);
      setSelectedRunMeta(prev => {
        const next = { ...prev };
        runs.forEach(run => {
          if (run.filename) {
            next[run.filename] = run;
          }
        });
        return next;
      });
      setHistoryTotal(data.total || 0);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingHistory(false);
    }
  };

  fetchHistoryRef.current = fetchHistory;

  const fetchCacheStatus = async () => {
    setLoadingCache(true);
    try {
      const res = await fetch(`${API_BASE}/api/cache-status`);
      if (!res.ok) throw new Error('Cache status unavailable.');
      const data = await res.json();
      setCacheStatus(data);
    } catch (err) {
      console.error('Cache status fetch failed:', err);
      setCacheStatus(null);
    } finally {
      setLoadingCache(false);
    }
  };

  const fetchComparison = async () => {
    setLoadingCompare(true);
    try {
      const runsParam = selectedRunsForCompare.join(',');
      const res = await fetch(`${API_BASE}/api/results/compare?exchange=${exchange}&runs=${runsParam}`);
      if (!res.ok) throw new Error("Failed to compare runs.");
      const runs = await res.json();

      // Format data for Recharts overlay
      // We align by step index (day index)
      setSelectedRunMeta(prev => {
        const next = { ...prev };
        runs.forEach((run, index) => {
          const filename = run.filename || selectedRunsForCompare[index];
          if (filename) {
            next[filename] = {
              ...next[filename],
              filename,
              alias: run.alias,
              exchange: run.exchange,
              trading_approach: run.trading_approach,
              prompt_version: run.prompt_version,
              initial_capital: run.initial_capital,
              final_capital: run.history?.[run.history.length - 1],
              pnl: run.history?.length ? run.history[run.history.length - 1] - (run.initial_capital || run.history[0]) : 0,
              date_range: run.date_range,
              metrics: run.metrics,
            };
          }
        });
        return next;
      });

      const maxLength = Math.max(...runs.map(r => r.history.length));
      const chartPoints = [];

      for (let i = 0; i < maxLength; i++) {
        const point = { day: i + 1 };
        runs.forEach((run, index) => {
          const filename = run.filename || selectedRunsForCompare[index];
          // If we have detailed history, retrieve calendar dates
          const detail = run.detailed_history && run.detailed_history[i];
          if (detail && detail.date) {
            point.date = detail.date;
          }
          if (filename) {
            point[filename] = run.history[i] !== undefined ? run.history[i] : null;
          }
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
    if (!filename) return;
    try {
      const res = await fetch(`${API_BASE}/api/results/${exchange}/${filename}`);
      if (!res.ok) throw new Error("Failed to load run details.");
      const data = await res.json();
      setSingleRunDetails(data);
      setSelectedHistoryFile(filename);
    } catch (err) {
      console.error("Error loading run details:", err);
      alert(`Failed to load run details: ${err.message}`);
      setSingleRunDetails(null);
      setSelectedHistoryFile('');
    }
  };

  const deleteRun = async (filename) => {
    const confirmDelete = window.confirm(`You are about to delete the run "${filename}". Are you sure?`);
    if (!confirmDelete) return;

    try {
      const res = await fetch(`${API_BASE}/api/results/${exchange}/${filename}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete the run.");
      
      // Remove from selected comparison overlay list if it was selected
      setSelectedRunsForCompare(prev => prev.filter(f => f !== filename));
      setSelectedRunMeta(prev => {
        const next = { ...prev };
        delete next[filename];
        return next;
      });
      // Refresh current history runs list
      fetchHistory();
    } catch (err) {
      alert(`Error deleting run: ${err.message}`);
    }
  };

  const startBacktest = async () => {
    if (runnerStatus === 'running') return;
    try {
      const res = await fetch(`${API_BASE}/api/backtest/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model_index: selectedModelIndex,
          exchange: exchange,
          start_date: startDateInput || null,
          end_date: endDateInput || null,
          cash: parseFloat(initialCashInput) || 1000000,
          trading_approach: tradingApproach
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

  const formatRunCapital = (run) => {
    if (!run || run.initial_capital === undefined || run.initial_capital === null) return '-';
    const sym = run.exchange === 'BIST30' ? '₺' : '$';
    return `${sym}${run.initial_capital.toLocaleString()}`;
  };

  // Helper selectors
  const toggleCompareRun = (filename) => {
    const targetRun = historyList.find(h => h.filename === filename) || selectedRunMeta[filename];
    if (!targetRun) return;

    setSelectedRunsForCompare(prev => {
      if (prev.includes(filename)) {
        return prev.filter(f => f !== filename);
      } else {
        // Check if there are already selected runs and if they have the same budget
        if (prev.length > 0) {
          const firstSelectedFilename = prev[0];
          const firstSelectedRun = selectedRunMeta[firstSelectedFilename] || historyList.find(h => h.filename === firstSelectedFilename);
          if (firstSelectedRun && firstSelectedRun.initial_capital !== targetRun.initial_capital) {
            alert(`You can only compare runs with the same budget. Selected budget: ${formatRunCapital(firstSelectedRun)}, target budget: ${formatRunCapital(targetRun)}.`);
            return prev;
          }
        }
        setSelectedRunMeta(current => ({
          ...current,
          [filename]: targetRun
        }));
        return [...prev, filename];
      }
    });
  };

  // Format currency
  const formatCurrency = (val) => {
    if (val === undefined || val === null) return '-';
    return `${currencySymbol}${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  // Format YYYY-MM-DD to DD.MM.YYYY
  const formatDateStr = (dStr) => {
    if (!dStr) return '';
    const parts = dStr.split('-');
    if (parts.length === 3) {
      return `${parts[2]}.${parts[1]}.${parts[0]}`;
    }
    return dStr;
  };

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

  const COLORS = [
    '#3b82f6', '#10b981', '#ef4444', '#f59e0b', '#8b5cf6', 
    '#ec4899', '#06b6d4', '#f97316', '#14b8a6', '#a855f7', 
    '#eab308', '#6366f1', '#adfa1d', '#f43f5e', '#0284c7', 
    '#b45309', '#4d7c0f', '#047857', '#0369a1', '#1d4ed8', 
    '#4338ca', '#6d28d9', '#7e22ce', '#a21caf', '#be185d', 
    '#be123c', '#b91c1c', '#c2410c', '#854d0e', '#15803d', 
    '#0f766e', '#0e7490'
  ];

  const totalPages = Math.ceil(historyTotal / 20) || 1;
  const getPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (historyPage > 3) pages.push('...');
      const start = Math.max(2, historyPage - 1);
      const end = Math.min(totalPages - 1, historyPage + 1);
      for (let i = start; i <= end; i++) pages.push(i);
      if (historyPage < totalPages - 2) pages.push('...');
      pages.push(totalPages);
    }
    return pages;
  };

  const isLight = theme === 'light';
  const chartGridColor = isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.03)';
  const chartAxisColor = isLight ? '#64748b' : '#475569';
  const chartTooltipBg = isLight ? '#ffffff' : '#0f111a';
  const chartTooltipBorder = isLight ? '#cbd5e1' : '#1e293b';
  const chartTooltipColor = isLight ? '#0f172a' : '#f1f5f9';

  return (
    <div className="flex h-screen bg-background text-slate-100 font-sans select-none flex-col">


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
                <div className="space-y-1.5 text-[10px] bg-slate-900/60 p-2 rounded border border-border font-mono">
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
                  onClick={() => setExchange('NASDAQ')}
                  className={`py-1.5 rounded-md text-xs font-bold transition-all ${
                    exchange === 'NASDAQ'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  NASDAQ (USD)
                </button>
                <button
                  onClick={() => setExchange('BIST30')}
                  className={`py-1.5 rounded-md text-xs font-bold transition-all ${
                    exchange === 'BIST30'
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                  }`}
                >
                  BIST30 (TRY)
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
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
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
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
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
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
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
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
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
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
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

            <div className="flex items-center gap-6 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-500 font-mono">Theme Selection:</span>
                <button
                  onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                  className="p-2 rounded-lg bg-slate-900 border border-border hover:bg-slate-800 text-slate-400 hover:text-blue-400 transition-all cursor-pointer flex items-center justify-center"
                  title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
                >
                  {theme === 'dark' ? (
                    <Sun className="h-4 w-4" />
                  ) : (
                    <Moon className="h-4 w-4" />
                  )}
                </button>
              </div>

              <div className="flex items-center gap-2 border-l border-border pl-6">
                <span className="text-slate-500 font-mono">Currency:</span>
                <span className="text-slate-300 font-extrabold bg-slate-900 border border-border px-2.5 py-1 rounded">
                  {currencyCode} ({currencySymbol})
                </span>
              </div>
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
              <DashboardOverview
                configData={configData}
                exchange={exchange}
                historyList={historyList}
                historyTotal={historyTotal}
                historyPage={historyPage}
                setHistoryPage={setHistoryPage}
                selectedRunsForCompare={selectedRunsForCompare}
                selectedRunMeta={selectedRunMeta}
                toggleCompareRun={toggleCompareRun}
                formatRunCapital={formatRunCapital}
                formatCurrency={formatCurrency}
                formatDateStr={formatDateStr}
                loadRunDetails={loadRunDetails}
                setSubTab={setSubTab}
                deleteRun={deleteRun}
                compareData={compareData}
                chartGridColor={chartGridColor}
                chartAxisColor={chartAxisColor}
                chartTooltipBg={chartTooltipBg}
                chartTooltipBorder={chartTooltipBorder}
                chartTooltipColor={chartTooltipColor}
                COLORS={COLORS}
                currencyCode={currencyCode}
                totalPages={totalPages}
                getPageNumbers={getPageNumbers}
              />
            )}

            {/* TAB 2: MODEL PORTFOLIO INSIGHTS */}
            {subTab === 'insights' && (
              <ModelInsights
                selectedHistoryFile={selectedHistoryFile}
                loadRunDetails={loadRunDetails}
                historyList={historyList}
                singleRunDetails={singleRunDetails}
                chartGridColor={chartGridColor}
                chartAxisColor={chartAxisColor}
                chartTooltipBg={chartTooltipBg}
                chartTooltipBorder={chartTooltipBorder}
                chartTooltipColor={chartTooltipColor}
                formatCurrency={formatCurrency}
                COLORS={COLORS}
              />
            )}

            {/* TAB 3: TRADE LEDGER */}
            {subTab === 'ledger' && (
              <TradeLedger
                selectedHistoryFile={selectedHistoryFile}
                loadRunDetails={loadRunDetails}
                historyList={historyList}
                ledgerActionFilter={ledgerActionFilter}
                setLedgerActionFilter={setLedgerActionFilter}
                ledgerFilter={ledgerFilter}
                setLedgerFilter={setLedgerFilter}
                singleRunDetails={singleRunDetails}
                formatCurrency={formatCurrency}
              />
            )}

            {/* TAB 4: MARKET & NEWS */}
            {subTab === 'market' && (
              <MarketNews
                exchange={exchange}
                marketData={marketData}
                loadingMarket={loadingMarket}
                newsData={newsData}
                loadingNews={loadingNews}
                formatCurrency={formatCurrency}
              />
            )}

            {/* TAB 5: BACKTEST RUNNER */}
            {subTab === 'runner' && (
              <BacktestRunner
                runnerStatus={runnerStatus}
                selectedModelIndex={selectedModelIndex}
                setSelectedModelIndex={setSelectedModelIndex}
                configData={configData}
                tradingApproach={tradingApproach}
                setTradingApproach={setTradingApproach}
                startDateInput={startDateInput}
                setStartDateInput={setStartDateInput}
                endDateInput={endDateInput}
                setEndDateInput={setEndDateInput}
                initialCashInput={initialCashInput}
                setInitialCashInput={setInitialCashInput}
                currencySymbol={currencySymbol}
                cacheStatus={cacheStatus}
                exchange={exchange}
                fetchCacheStatus={fetchCacheStatus}
                loadingCache={loadingCache}
                cancelBacktest={cancelBacktest}
                startBacktest={startBacktest}
                runnerProgress={runnerProgress}
                runnerLogs={runnerLogs}
                runnerExitCode={runnerExitCode}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
