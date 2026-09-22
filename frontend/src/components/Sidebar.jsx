import React from 'react';
import { 
  Activity, 
  GraduationCap, 
  Users, 
  Bot, 
  Settings, 
  RefreshCw, 
  Calendar, 
  ChevronRight,
  Sparkles,
  LayoutDashboard,
  CheckCircle2,
  AlertCircle,
  Lock
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  workspace,
  setWorkspace,
  garminStatus,
  onSyncGarmin,
  isSyncing,
  urgentDeadlineCount = 0,
  peopleCount = 0,
  onLock
}) {
  const handleNavClick = (tab) => {
    setActiveTab(tab);
    if (tab === 'daily') setWorkspace('life');
    if (tab === 'uni') setWorkspace('uni');
  };

  return (
    <aside className="w-64 bg-slate-900/95 border-r border-slate-800/80 flex flex-col justify-between h-screen sticky top-0 z-40 backdrop-blur-md select-none">
      <div className="p-5 space-y-6">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 via-teal-400 to-cyan-500 p-[2px] shadow-lg shadow-emerald-950/40">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-black tracking-tight text-white text-base">COMMAND</span>
              <span className="text-xs font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                2.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">Life & Academic OS</p>
          </div>
        </div>

        {/* Workspace Switcher Pill */}
        <div className="bg-slate-950 p-1 rounded-xl border border-slate-800">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-2 py-1">
            Active Workspace
          </div>
          <div className="grid grid-cols-2 gap-1 mt-0.5">
            <button
              onClick={() => {
                setWorkspace('life');
                if (activeTab === 'uni') setActiveTab('daily');
              }}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-bold transition-all ${
                workspace === 'life'
                  ? 'bg-emerald-600 text-white shadow-md shadow-emerald-950/50'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Life</span>
            </button>

            <button
              onClick={() => {
                setWorkspace('uni');
                if (activeTab === 'daily') setActiveTab('uni');
              }}
              className={`flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-lg text-xs font-bold transition-all relative ${
                workspace === 'uni'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-950/50'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <GraduationCap className="w-3.5 h-3.5" />
              <span>University</span>
              {urgentDeadlineCount > 0 && (
                <span className="w-2 h-2 rounded-full bg-rose-400 absolute top-1 right-1 animate-ping" />
              )}
            </button>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="space-y-1">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500 px-3 py-1">
            Navigation
          </div>

          <button
            onClick={() => handleNavClick('daily')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'daily'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <LayoutDashboard className="w-4 h-4 text-emerald-400" />
              <span>Day-to-Day Life</span>
            </div>
          </button>

          <button
            onClick={() => handleNavClick('uni')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'uni'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <GraduationCap className="w-4 h-4 text-indigo-400" />
              <span>University</span>
            </div>
            {urgentDeadlineCount > 0 && (
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                {urgentDeadlineCount} urgent
              </span>
            )}
          </button>

          <button
            onClick={() => handleNavClick('people')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'people'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Users className="w-4 h-4 text-cyan-400" />
              <span>People Network</span>
            </div>
            {peopleCount > 0 && (
              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                {peopleCount}
              </span>
            )}
          </button>

          <button
            onClick={() => handleNavClick('chat')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'chat'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <div className="relative">
                <Bot className="w-4 h-4 text-amber-400" />
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 absolute -top-0.5 -right-0.5" />
              </div>
              <span className="text-amber-200">AI Assistant</span>
            </div>
            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              Omniscient
            </span>
          </button>

          <button
            onClick={() => handleNavClick('settings')}
            className={`w-full flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition ${
              activeTab === 'settings'
                ? 'bg-slate-800 text-white shadow-sm border border-slate-700/80'
                : 'text-slate-400 hover:text-white hover:bg-slate-900'
            }`}
          >
            <div className="flex items-center gap-2.5">
              <Settings className="w-4 h-4 text-slate-400" />
              <span>Settings & Sync</span>
            </div>
          </button>

          {onLock && (
            <button
              onClick={onLock}
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition text-slate-400 hover:text-rose-400 hover:bg-rose-500/10"
              title="Lock this workspace session"
            >
              <div className="flex items-center gap-2.5">
                <Lock className="w-4 h-4 text-slate-400" />
                <span>Lock Workspace</span>
              </div>
            </button>
          )}
        </nav>
      </div>

      {/* Footer Garmin Sync Status */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/60 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${
              garminStatus?.configured ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'
            }`} />
            <span className="text-xs font-medium text-slate-300">
              {garminStatus?.configured ? 'Garmin Live' : 'Garmin Demo'}
            </span>
          </div>
          <button
            onClick={onSyncGarmin}
            disabled={isSyncing}
            className={`p-1.5 rounded-lg border text-xs transition ${
              isSyncing
                ? 'bg-slate-800 text-slate-500 border-slate-700'
                : 'bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border-slate-700'
            }`}
            title="Sync Garmin data"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-emerald-400' : ''}`} />
          </button>
        </div>

        <div className="text-[10px] text-slate-500">
          Last sync: <span className="text-slate-400 font-mono">{garminStatus?.last_sync ? new Date(garminStatus.last_sync).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Ready'}</span>
        </div>
      </div>
    </aside>
  );
}
