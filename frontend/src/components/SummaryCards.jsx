import React from 'react';
import { 
  Footprints, 
  Flame, 
  Moon, 
  Heart, 
  TrendingUp, 
  TrendingDown, 
  Sparkles, 
  Utensils, 
  Zap, 
  Smile 
} from 'lucide-react';
import ProgressRing from './ProgressRing';

export default function SummaryCards({ metrics, journalEntries = [] }) {
  // Aggregate nutrition across all journal entries for this date
  const totalCaloriesConsumed = journalEntries.reduce((acc, entry) => {
    return acc + (entry?.nutrition?.total_calories || 0);
  }, 0);

  const steps = metrics?.steps || 0;
  const stepGoal = metrics?.step_goal || 10000;
  const stepPercent = Math.round((steps / stepGoal) * 100);
  const distanceKm = ((metrics?.distance_meters || 0) / 1000).toFixed(2);

  const caloriesBurned = metrics?.total_calories_burned || (metrics?.active_calories || 0) + (metrics?.resting_calories || 1850);
  const activeCalories = metrics?.active_calories || 0;
  const restingCalories = metrics?.resting_calories || 1850;

  const netCalorieDiff = caloriesBurned - totalCaloriesConsumed;
  const isDeficit = netCalorieDiff >= 0;

  // Sleep format
  const sleepSecs = metrics?.sleep_seconds || 0;
  const sleepHours = Math.floor(sleepSecs / 3600);
  const sleepMins = Math.floor((sleepSecs % 3600) / 60);
  const sleepScore = metrics?.sleep_score || null;

  // Resting HR
  const restingHR = metrics?.resting_heart_rate || null;

  // Latest journal mood and summary
  const latestEntry = journalEntries[0];
  const mood = latestEntry?.mood || null;
  const summary = latestEntry?.summary || null;
  const tags = latestEntry?.tags || [];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {/* 1. Steps Card */}
      <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-emerald-500/40 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg border border-emerald-500/20">
              <Footprints className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Garmin Steps</span>
          </div>
          <span className="text-xs font-mono font-bold text-emerald-400">
            {stepPercent}% Goal
          </span>
        </div>

        <div className="flex items-center justify-between pt-1">
          <div>
            <div className="text-2xl sm:text-3xl font-black text-white tracking-tight">
              {steps.toLocaleString()}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">
              Goal: {stepGoal.toLocaleString()} steps
            </div>
            <div className="flex items-center gap-2 mt-3 text-xs font-medium text-slate-300">
              <span className="px-2 py-0.5 rounded bg-slate-800 text-emerald-300 border border-slate-700">
                {distanceKm} km
              </span>
              <span className="text-slate-500">•</span>
              <span className="text-slate-400">{activeCalories} active kcal</span>
            </div>
          </div>

          <ProgressRing progress={stepPercent} size={82} strokeWidth={8}>
            <span className="text-xs font-bold text-white font-mono">{stepPercent}%</span>
          </ProgressRing>
        </div>
      </div>

      {/* 2. Caloric Balance Card */}
      <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-amber-500/40 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg border border-amber-500/20">
              <Flame className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Energy Balance</span>
          </div>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider border ${
            isDeficit 
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' 
              : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
          }`}>
            {isDeficit ? 'Deficit' : 'Surplus'}
          </span>
        </div>

        <div className="space-y-3">
          <div className="flex items-baseline justify-between">
            <div>
              <span className="text-2xl font-black text-white">{caloriesBurned.toLocaleString()}</span>
              <span className="text-xs text-slate-400 ml-1">kcal burned</span>
            </div>
            <div className="text-right">
              <span className="text-lg font-bold text-amber-300">{totalCaloriesConsumed.toLocaleString()}</span>
              <span className="text-xs text-slate-400 ml-1">eaten</span>
            </div>
          </div>

          {/* Progress split bar */}
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
            <div 
              className="bg-emerald-500 h-full rounded-full transition-all duration-700"
              style={{ width: `${Math.min(100, (caloriesBurned / 3000) * 100)}%` }}
              title={`Burned: ${caloriesBurned} kcal`}
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-400 pt-1 border-t border-slate-800/80">
            <span className="flex items-center gap-1">
              <Utensils className="w-3 h-3 text-amber-400" />
              Journal Food Log
            </span>
            <span className="font-semibold text-slate-200">
              {Math.abs(netCalorieDiff)} kcal {isDeficit ? 'net deficit' : 'net surplus'}
            </span>
          </div>
        </div>
      </div>

      {/* 3. Sleep & Recovery Card */}
      <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-indigo-500/40 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20">
              <Moon className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Sleep & Recovery</span>
          </div>
          {sleepScore && (
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono">
              Score: {sleepScore}
            </span>
          )}
        </div>

        <div className="pt-1">
          <div className="text-2xl sm:text-3xl font-black text-white tracking-tight">
            {sleepSecs > 0 ? `${sleepHours}h ${sleepMins}m` : '--'}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            Total Sleep Duration
          </div>

          <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-800/80 text-xs">
            <div className="flex items-center gap-1.5 text-slate-300">
              <Heart className="w-3.5 h-3.5 text-rose-400 fill-rose-500/20" />
              <span>Resting HR: <strong className="text-white font-mono">{restingHR ? `${restingHR} bpm` : '--'}</strong></span>
            </div>
            {sleepScore ? (
              <span className="text-emerald-400 font-medium text-[11px]">Recovery Logged</span>
            ) : (
              <span className="text-slate-500 text-[11px]">Pending Sync</span>
            )}
          </div>
        </div>
      </div>

      {/* 4. Day Wellness & Mood Card */}
      <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-lg relative overflow-hidden group hover:border-cyan-500/40 transition">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg border border-cyan-500/20">
              <Sparkles className="w-4 h-4" />
            </div>
            <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">Mood & Focus</span>
          </div>
          {mood && (
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
              {mood}
            </span>
          )}
        </div>

        <div className="pt-1">
          {summary ? (
            <p className="text-xs text-slate-300 line-clamp-2 italic leading-relaxed min-h-[36px]">
              "{summary}"
            </p>
          ) : (
            <p className="text-xs text-slate-500 italic leading-relaxed min-h-[36px]">
              Log a journal entry to see your mood & focus summary here.
            </p>
          )}

          <div className="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-slate-800/80">
            {tags.length > 0 ? (
              tags.map((t, idx) => (
                <span 
                  key={idx} 
                  className="text-[10px] px-2 py-0.5 rounded bg-slate-800/90 text-slate-300 font-mono border border-slate-700/60"
                >
                  #{t}
                </span>
              ))
            ) : (
              <span className="text-[10px] text-slate-500 italic">No tags logged</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
