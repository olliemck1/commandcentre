import React from 'react';
import { 
  Activity, 
  Flame, 
  Clock, 
  MapPin, 
  Utensils, 
  Users, 
  CheckCircle, 
  Heart,
  ChevronRight
} from 'lucide-react';

export default function DailyTimeline({ metrics, journalEntries = [], onPersonClick }) {
  const activities = metrics?.activities || [];

  // Build unified timeline events
  const timelineEvents = [];

  // 1. Add Garmin activities
  activities.forEach((act, idx) => {
    timelineEvents.push({
      id: `garmin-${act.id || idx}`,
      type: 'garmin_activity',
      time: act.start_time || '07:30',
      title: act.name,
      category: act.type,
      duration: `${act.duration_mins} min`,
      distance: act.distance_km > 0 ? `${act.distance_km} km` : null,
      calories: `${act.calories} kcal`,
      avg_hr: act.avg_hr ? `${act.avg_hr} bpm` : null,
      color: 'emerald'
    });
  });

  // 2. Add Journal entries
  journalEntries.forEach((entry) => {
    const timeStr = entry.created_at 
      ? new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : '12:00';

    // Meals
    if (entry.nutrition?.items?.length > 0) {
      timelineEvents.push({
        id: `journal-meal-${entry.id}`,
        type: 'meal',
        time: timeStr,
        title: 'Nutritional Intake',
        description: entry.nutrition.items.map(i => `${i.name} (${i.portion})`).join(', '),
        calories: `${entry.nutrition.total_calories} kcal`,
        macros: `P:${entry.nutrition.total_protein_g}g C:${entry.nutrition.total_carbs_g}g F:${entry.nutrition.total_fat_g}g`,
        color: 'amber'
      });
    }

    // Social interactions
    if (entry.people?.length > 0) {
      entry.people.forEach((p, pIdx) => {
        timelineEvents.push({
          id: `journal-social-${entry.id}-${pIdx}`,
          type: 'social',
          time: timeStr,
          title: `Interaction with ${p.name}`,
          person_name: p.name,
          location: p.location,
          context: p.context,
          facts: p.facts_learned,
          sentiment: p.sentiment,
          color: 'cyan'
        });
      });
    }

    // Reflection if neither
    if (!entry.nutrition?.items?.length && !entry.people?.length) {
      timelineEvents.push({
        id: `journal-ref-${entry.id}`,
        type: 'journal',
        time: timeStr,
        title: entry.mood ? `${entry.mood} Reflection` : 'Daily Journal Log',
        description: entry.summary || entry.raw_text,
        color: 'slate'
      });
    }
  });

  // Sort events by time string
  timelineEvents.sort((a, b) => a.time.localeCompare(b.time));

  return (
    <div className="bg-slate-900/90 border border-slate-800/80 rounded-2xl p-5 shadow-xl flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white tracking-tight">Daily Activity & Social Feed</h2>
            <p className="text-xs text-slate-400">Consolidated chronological timeline of workouts, meals, and meetings</p>
          </div>
        </div>
        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
          {timelineEvents.length} events
        </span>
      </div>

      {/* Timeline Feed */}
      <div className="mt-4 flex-1 overflow-y-auto pr-1">
        {timelineEvents.length === 0 ? (
          <div className="text-center py-12 border border-dashed border-slate-800/80 rounded-xl">
            <Activity className="w-8 h-8 text-slate-600 mx-auto mb-2 opacity-50" />
            <p className="text-xs text-slate-500">No activities or events recorded for this date.</p>
            <p className="text-[11px] text-slate-600 mt-1">Sync Garmin or save a journal entry to populate the timeline!</p>
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-slate-800">
            {timelineEvents.map((evt) => {
              return (
                <div key={evt.id} className="relative group">
                  {/* Bullet indicator */}
                  <div className={`absolute -left-6 top-1.5 w-5 h-5 rounded-full border-2 flex items-center justify-center transition ${
                    evt.color === 'emerald'
                      ? 'bg-emerald-950 border-emerald-500 text-emerald-400'
                      : evt.color === 'amber'
                      ? 'bg-amber-950 border-amber-500 text-amber-400'
                      : evt.color === 'cyan'
                      ? 'bg-cyan-950 border-cyan-500 text-cyan-400'
                      : 'bg-slate-900 border-slate-600 text-slate-400'
                  }`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${
                      evt.color === 'emerald' ? 'bg-emerald-400' :
                      evt.color === 'amber' ? 'bg-amber-400' :
                      evt.color === 'cyan' ? 'bg-cyan-400' : 'bg-slate-400'
                    }`} />
                  </div>

                  {/* Card Content */}
                  <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 space-y-2 hover:border-slate-700 transition">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[11px] font-bold text-slate-400 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                          {evt.time}
                        </span>
                        <span className="font-bold text-white text-xs">
                          {evt.title}
                        </span>
                      </div>

                      {evt.type === 'garmin_activity' && (
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          Garmin Workout
                        </span>
                      )}
                      {evt.type === 'meal' && (
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                          Meal
                        </span>
                      )}
                      {evt.type === 'social' && (
                        <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                          Social
                        </span>
                      )}
                    </div>

                    {/* Garmin Workout Details */}
                    {evt.type === 'garmin_activity' && (
                      <div className="flex flex-wrap items-center gap-3 text-xs text-slate-300 pt-1">
                        <span className="font-medium">{evt.duration}</span>
                        {evt.distance && (
                          <>
                            <span className="text-slate-600">•</span>
                            <span className="text-emerald-400 font-bold">{evt.distance}</span>
                          </>
                        )}
                        <span className="text-slate-600">•</span>
                        <span className="text-amber-400 font-bold">{evt.calories}</span>
                        {evt.avg_hr && (
                          <>
                            <span className="text-slate-600">•</span>
                            <span className="text-rose-400 flex items-center gap-1 font-mono">
                              <Heart className="w-3 h-3 fill-rose-500/30" />
                              {evt.avg_hr}
                            </span>
                          </>
                        )}
                      </div>
                    )}

                    {/* Meal details */}
                    {evt.type === 'meal' && (
                      <div className="text-xs space-y-1 pt-0.5">
                        <p className="text-slate-300 leading-relaxed font-medium">{evt.description}</p>
                        <div className="flex items-center gap-2 pt-1 text-[11px] font-mono">
                          <span className="text-amber-400 font-bold">{evt.calories}</span>
                          <span className="text-slate-600">•</span>
                          <span className="text-slate-400">{evt.macros}</span>
                        </div>
                      </div>
                    )}

                    {/* Social details */}
                    {evt.type === 'social' && (
                      <div className="text-xs space-y-1.5 pt-0.5">
                        {evt.context && (
                          <p className="text-slate-300 leading-relaxed italic">
                            {evt.context}
                          </p>
                        )}
                        <div className="flex items-center justify-between pt-1">
                          <div className="flex items-center gap-2">
                            {evt.location && (
                              <span className="flex items-center gap-1 text-[10px] text-slate-400 px-2 py-0.5 rounded bg-slate-900 border border-slate-800">
                                <MapPin className="w-2.5 h-2.5 text-slate-500" />
                                {evt.location}
                              </span>
                            )}
                            <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 capitalize">
                              {evt.sentiment}
                            </span>
                          </div>

                          <button
                            onClick={() => onPersonClick && onPersonClick(evt.person_name)}
                            className="text-[11px] font-bold text-cyan-400 hover:text-cyan-300 flex items-center gap-0.5 transition"
                          >
                            <span>Profile</span>
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
