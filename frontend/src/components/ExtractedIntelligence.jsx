import React from 'react';
import { 
  Utensils, 
  Users, 
  MapPin, 
  ThumbsUp, 
  Smile, 
  Info, 
  Sparkles,
  ExternalLink
} from 'lucide-react';

export default function ExtractedIntelligence({ 
  nutrition, 
  people = [], 
  summary, 
  onPersonClick 
}) {
  const items = nutrition?.items || [];
  const totalCals = nutrition?.total_calories || 0;
  const p = nutrition?.total_protein_g || 0;
  const c = nutrition?.total_carbs_g || 0;
  const f = nutrition?.total_fat_g || 0;

  const totalMacros = p + c + f || 1;
  const pPct = Math.round((p / totalMacros) * 100);
  const cPct = Math.round((c / totalMacros) * 100);
  const fPct = Math.round((f / totalMacros) * 100);

  return (
    <div className="space-y-4 text-xs">
      {/* 1. Nutrition Analysis */}
      {items.length > 0 || totalCals > 0 ? (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-bold text-amber-300">
              <Utensils className="w-3.5 h-3.5 text-amber-400" />
              <span>Parsed Nutrition Breakdown</span>
            </div>
            <span className="font-mono font-black text-white px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
              {totalCals} kcal
            </span>
          </div>

          {/* Macro Split Bar */}
          <div className="space-y-1">
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
              <div className="bg-emerald-500 h-full" style={{ width: `${pPct}%` }} title={`Protein: ${p}g (${pPct}%)`} />
              <div className="bg-amber-500 h-full" style={{ width: `${cPct}%` }} title={`Carbs: ${c}g (${cPct}%)`} />
              <div className="bg-rose-500 h-full" style={{ width: `${fPct}%` }} title={`Fat: ${f}g (${fPct}%)`} />
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-0.5">
              <span className="text-emerald-400">P: {p}g ({pPct}%)</span>
              <span className="text-amber-400">C: {c}g ({cPct}%)</span>
              <span className="text-rose-400">F: {f}g ({fPct}%)</span>
            </div>
          </div>

          {/* Itemized Items */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 pt-1">
            {items.map((item, idx) => (
              <div 
                key={idx} 
                className="flex items-center justify-between bg-slate-950/60 px-2.5 py-1.5 rounded-lg border border-slate-800/80 text-[11px]"
              >
                <div className="truncate">
                  <span className="font-medium text-slate-200">{item.name}</span>
                  <span className="text-slate-500 text-[10px] ml-1">({item.portion})</span>
                </div>
                <span className="font-mono font-bold text-amber-300 shrink-0 ml-2">
                  {item.calories} cal
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {/* 2. Detected People & Social Insights */}
      {people.length > 0 ? (
        <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 font-bold text-cyan-300">
              <Users className="w-3.5 h-3.5 text-cyan-400" />
              <span>Extracted Social & CRM Entities</span>
            </div>
            <span className="text-[10px] text-slate-400">
              Synced to Network CRM
            </span>
          </div>

          <div className="space-y-2">
            {people.map((person, idx) => (
              <div 
                key={idx}
                className="bg-slate-950/70 border border-slate-800/90 rounded-lg p-2.5 space-y-1.5 hover:border-cyan-500/30 transition"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-cyan-500/20 text-cyan-300 font-bold text-xs flex items-center justify-center border border-cyan-500/30">
                      {person.name[0]?.toUpperCase() || 'P'}
                    </div>
                    <button
                      type="button"
                      onClick={() => onPersonClick && onPersonClick(person.name)}
                      className="font-bold text-white hover:text-cyan-400 flex items-center gap-1 group transition"
                    >
                      <span>{person.name}</span>
                      <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 text-cyan-400 transition" />
                    </button>
                    {person.location && (
                      <span className="flex items-center gap-0.5 text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-800">
                        <MapPin className="w-2.5 h-2.5 text-slate-500" />
                        {person.location}
                      </span>
                    )}
                  </div>

                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                    person.sentiment === 'positive' 
                      ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      : person.sentiment === 'negative'
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                      : 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}>
                    {person.sentiment}
                  </span>
                </div>

                {/* Facts learned */}
                {person.facts_learned && person.facts_learned.length > 0 && (
                  <div className="pl-8 space-y-1">
                    {person.facts_learned.map((fact, fIdx) => (
                      <div key={fIdx} className="text-[11px] text-slate-300 flex items-start gap-1.5">
                        <span className="text-cyan-400 font-black">•</span>
                        <span>{fact}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
