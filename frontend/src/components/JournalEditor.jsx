import React, { useState } from 'react';
import { 
  BookOpen, 
  Send, 
  Sparkles, 
  Trash2, 
  Clock, 
  Utensils, 
  Users, 
  Tag, 
  CheckCircle2,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import ExtractedIntelligence from './ExtractedIntelligence';

const PROMPT_SUGGESTIONS = [
  {
    label: "🍳 Morning Routine",
    text: "Light breakfast: 2 scrambled eggs, sourdough toast, and an espresso (approx 380 kcal)."
  },
  {
    label: "🥗 Lunch Log",
    text: "Lunch was a grilled chicken salad with quinoa and olive oil (approx 620 kcal)."
  },
  {
    label: "🏃 Workout & Dinner",
    text: "Afternoon gym workout. Dinner was salmon fillet with roasted sweet potatoes and broccoli (around 700 kcal)."
  }
];

export default function JournalEditor({ 
  selectedDate, 
  journalEntries = [], 
  onSubmitEntry, 
  onDeleteEntry,
  onPersonClick,
  isSubmitting 
}) {
  const [text, setText] = useState('');
  const [expandedEntryId, setExpandedEntryId] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!text.trim() || isSubmitting) return;

    await onSubmitEntry(text);
    setText('');
  };

  const handleApplySuggestion = (suggestionText) => {
    setText(suggestionText);
  };

  const toggleExpand = (id) => {
    setExpandedEntryId(expandedEntryId === id ? null : id);
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-xl flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-xl border border-emerald-500/20">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Daily Journal & AI Extractor</h2>
            <p className="text-xs text-slate-400">Log meals, thoughts, and conversations for structured extraction</p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
          {journalEntries.length} {journalEntries.length === 1 ? 'entry' : 'entries'}
        </span>
      </div>

      {/* Input Form */}
      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <div className="relative">
          <textarea
            rows={4}
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="What did you eat, who did you meet, or what happened today? (e.g. 'Oatmeal & flat white for breakfast around 450 cal. Study session in library...')"
            className="w-full bg-slate-950/90 border border-slate-800 rounded-xl p-3.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500/80 focus:ring-1 focus:ring-emerald-500/40 transition resize-none leading-relaxed"
          />
        </div>

        {/* Quick prompt templates */}
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-[11px] text-slate-500 font-medium">Quick Starters:</span>
          {PROMPT_SUGGESTIONS.map((item, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleApplySuggestion(item.text)}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition"
            >
              {item.label}
            </button>
          ))}
        </div>

        {/* Submit action */}
        <div className="flex items-center justify-end pt-1">
          <button
            type="submit"
            disabled={!text.trim() || isSubmitting}
            className={`flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold transition shadow-lg ${
              !text.trim() || isSubmitting
                ? 'bg-slate-800 text-slate-500 border border-slate-700/50 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/60 active:scale-95'
            }`}
          >
            <Sparkles className={`w-4 h-4 ${isSubmitting ? 'animate-spin' : ''}`} />
            <span>{isSubmitting ? 'Extracting Insights...' : 'Analyze & Save Entry'}</span>
          </button>
        </div>
      </form>

      {/* Entry History & Extracted Output List */}
      <div className="mt-6 pt-4 border-t border-slate-800/80 flex-1 overflow-y-auto space-y-4 pr-1">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
          Logged Entries for Today
        </h3>

        {journalEntries.length === 0 ? (
          <div className="text-center py-8 border border-dashed border-slate-800/80 rounded-xl">
            <p className="text-xs text-slate-500">No journal entries saved for this date.</p>
            <p className="text-[11px] text-slate-600 mt-1">Type in the box above or pick a starter to log meals and friends!</p>
          </div>
        ) : (
          journalEntries.map((entry) => {
            const isExpanded = expandedEntryId === entry.id || journalEntries.length === 1;

            return (
              <div 
                key={entry.id}
                className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-4 space-y-3 transition hover:border-slate-700/80"
              >
                {/* Header row */}
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1">
                    <p className="text-sm text-slate-200 leading-relaxed font-normal">
                      "{entry.raw_text}"
                    </p>
                    <div className="flex items-center gap-2 mt-2 text-[11px] text-slate-400">
                      <Clock className="w-3 h-3" />
                      <span>{entry.created_at ? new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Today'}</span>
                      <span className="text-slate-600">•</span>
                      <span className="px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-medium">
                        {entry.mood || 'Balanced'}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => toggleExpand(entry.id)}
                      className="p-1 text-slate-400 hover:text-white rounded hover:bg-slate-800"
                      title={isExpanded ? "Collapse extracted details" : "Expand extracted details"}
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                    <button
                      onClick={() => onDeleteEntry(entry.id)}
                      className="p-1 text-slate-500 hover:text-rose-400 rounded hover:bg-rose-950/30"
                      title="Delete entry"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Extracted Intelligence Details */}
                {isExpanded && (
                  <div className="pt-2 border-t border-slate-800/80">
                    <ExtractedIntelligence 
                      nutrition={entry.nutrition} 
                      people={entry.people} 
                      summary={entry.summary} 
                      onPersonClick={onPersonClick}
                    />
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
