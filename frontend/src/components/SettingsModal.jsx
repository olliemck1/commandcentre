import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Activity, 
  Key, 
  Database, 
  RefreshCw, 
  CheckCircle2, 
  AlertCircle, 
  Sparkles, 
  Folder,
  ShieldCheck,
  Check
} from 'lucide-react';
import { fetchLLMStatus } from '../api/client';

export default function SettingsModal({ 
  garminStatus, 
  onRefreshGarminStatus 
}) {
  const [llmStatus, setLlmStatus] = useState(null);
  const [testingLlm, setTestingLlm] = useState(false);
  const [llmMessage, setLlmMessage] = useState('');

  useEffect(() => {
    checkLLM();
  }, []);

  const checkLLM = async () => {
    setTestingLlm(true);
    setLlmMessage('');
    try {
      const stat = await fetchLLMStatus();
      setLlmStatus(stat);
      if (stat.valid) {
        setLlmMessage(`Google Gemini connection verified! Model: ${stat.model}`);
      } else if (stat.configured) {
        setLlmMessage(`Key configured but test failed: ${stat.error || 'Check API permissions'}`);
      }
    } catch (err) {
      setLlmMessage(`Failed to reach status endpoint: ${err.message}`);
    } finally {
      setTestingLlm(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              Settings & Service Integration
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Active configuration for Google Gemini AI, Garmin Connect telemetry, and Durham University data feeds
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 1. Garmin Connect Ingestion Service */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-emerald-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Garmin Connect Service
              </h2>
            </div>
            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
              garminStatus?.configured
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
            }`}>
              {garminStatus?.configured ? 'Credentials Set' : 'Awaiting Setup'}
            </span>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400">Status:</span>
              <span className="font-semibold text-slate-200">
                {garminStatus?.configured ? 'Credentials Configured in .env' : 'No credentials in .env'}
              </span>
            </div>
            {garminStatus?.email && (
              <div className="flex justify-between">
                <span className="text-slate-400">Account:</span>
                <span className="font-mono text-slate-200">{garminStatus.email}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-400">Token Cache:</span>
              <span className="text-slate-300 font-mono text-[11px]">.garmin_tokens/ (MFA session stored)</span>
            </div>
          </div>

          <div className="text-xs text-slate-400 space-y-1.5 leading-relaxed">
            <p className="font-semibold text-slate-300">Garmin Connection Details:</p>
            <p>1. Stored in <code className="text-emerald-400 font-mono">backend/.env</code></p>
            <p>2. Active email: <code className="text-slate-300 font-mono">{garminStatus?.email || 'GARMIN_EMAIL'}</code></p>
            <p>3. Session tokens persist in <code className="text-slate-300 font-mono">.garmin_tokens</code> to minimize rate limits.</p>
          </div>

          <button
            onClick={onRefreshGarminStatus}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition active:scale-95"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Check Garmin Connection
          </button>
        </div>

        {/* 2. Structured LLM Engine */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                AI Extraction Engine
              </h2>
            </div>
            <span className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
              llmStatus?.valid
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : llmStatus?.configured
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {llmStatus?.valid ? '✓ Gemini Active' : llmStatus?.configured ? 'Testing...' : 'Heuristic Mode'}
            </span>
          </div>

          <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400">Active Engine:</span>
              <span className="font-bold text-white">
                {llmStatus?.valid ? 'Google Gemini 3.6 Flash' : 'Built-in Heuristic NLP'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Model Version:</span>
              <span className="font-mono text-indigo-300 text-[11px]">
                {llmStatus?.model || 'gemini-3.6-flash'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">API Key Detected:</span>
              <span className={`font-semibold ${llmStatus?.configured ? 'text-emerald-400' : 'text-slate-400'}`}>
                {llmStatus?.configured ? 'Yes (configured in .env)' : 'None found'}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Output Format:</span>
              <span className="font-mono text-slate-300 text-[11px]">Strict JSON Schema & Tool Calling</span>
            </div>
          </div>

          {llmMessage && (
            <div className={`p-2.5 rounded-xl text-xs border ${
              llmStatus?.valid 
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60' 
                : 'bg-amber-950/40 text-amber-300 border-amber-800/60'
            }`}>
              {llmMessage}
            </div>
          )}

          <button
            onClick={checkLLM}
            disabled={testingLlm}
            className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg transition active:scale-95 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${testingLlm ? 'animate-spin' : ''}`} />
            <span>{testingLlm ? 'Testing Gemini API...' : 'Test & Verify Gemini Key'}</span>
          </button>
        </div>

        {/* 3. Durham University & Timetable Configuration */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl space-y-4 md:col-span-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-indigo-400" />
              <h2 className="text-sm font-bold text-white uppercase tracking-wider">
                Durham University Feeds & MongoDB Data Store
              </h2>
            </div>
            <span className="text-[11px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Live & Synced
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="font-bold text-slate-200">Durham MyTimetable Feed (.ics)</div>
              <p className="text-[11px] text-slate-400 font-mono break-all bg-slate-900/80 p-2 rounded border border-slate-800">
                https://mytimetable.durham.ac.uk/calendar/export/••••••••.ics
              </p>
              <p className="text-[11px] text-slate-400">
                Synchronizes active lectures, drop-in classes, and venues (CLC202, PH8, TLC123).
              </p>
            </div>

            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="font-bold text-slate-200">MongoDB Database (Remote Cluster)</div>
              <p className="text-[11px] text-slate-400 font-mono break-all bg-slate-900/80 p-2 rounded border border-slate-800">
                Collection: test.assignments (Synced via MONGODB_URI)
              </p>
              <p className="text-[11px] text-slate-400">
                Imported all historical assignments and timetable items into local SQLite database.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
