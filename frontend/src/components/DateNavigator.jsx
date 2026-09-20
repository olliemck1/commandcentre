import React from 'react';
import { ChevronLeft, ChevronRight, Calendar, Sparkles } from 'lucide-react';
import { 
  formatDisplayDate, 
  getRelativeDayLabel, 
  getPreviousDay, 
  getNextDay, 
  getTodayString 
} from '../utils/dateUtils';

export default function DateNavigator({ selectedDate, onDateChange }) {
  const today = getTodayString();
  const isToday = selectedDate === today;
  const relativeLabel = getRelativeDayLabel(selectedDate);

  const handlePrev = () => {
    onDateChange(getPreviousDay(selectedDate));
  };

  const handleNext = () => {
    onDateChange(getNextDay(selectedDate));
  };

  const handleToday = () => {
    onDateChange(today);
  };

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 py-2 border-b border-slate-800/60 mb-6">
      {/* Date display & Relative Pill */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-slate-900 border border-slate-800 rounded-xl text-emerald-400">
          <Calendar className="w-5 h-5" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
              {formatDisplayDate(selectedDate)}
            </h1>
            <span className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
              isToday 
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              {relativeLabel}
            </span>
          </div>
          <p className="text-xs text-slate-400">Daily telemetry, nutrition and social activity log</p>
        </div>
      </div>

      {/* Navigation Controls */}
      <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-xl border border-slate-800 shadow-inner">
        <button
          onClick={handlePrev}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          title="Previous Day"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <button
          onClick={handleToday}
          className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
            isToday
              ? 'bg-emerald-600 text-white shadow'
              : 'text-slate-300 hover:bg-slate-800'
          }`}
        >
          Today
        </button>

        <button
          onClick={handleNext}
          className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          title="Next Day"
        >
          <ChevronRight className="w-4 h-4" />
        </button>

        {/* Date picker input */}
        <div className="relative pl-1 border-l border-slate-800">
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => e.target.value && onDateChange(e.target.value)}
            className="bg-slate-900 hover:bg-slate-800/80 text-slate-300 text-xs rounded-lg px-2 py-1 outline-none border border-slate-700 focus:border-emerald-500 cursor-pointer transition font-mono"
          />
        </div>
      </div>
    </div>
  );
}
