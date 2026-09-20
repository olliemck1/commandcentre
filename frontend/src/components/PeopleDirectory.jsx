import React, { useState, useMemo } from 'react';
import { 
  Users, 
  Search, 
  Tag, 
  Calendar, 
  Sparkles, 
  ChevronRight, 
  Clock, 
  MessageSquare,
  Filter
} from 'lucide-react';
import { formatDisplayDate } from '../utils/dateUtils';

export default function PeopleDirectory({ 
  people = [], 
  onSelectPerson 
}) {
  const [search, setSearch] = useState('');
  const [selectedTag, setSelectedTag] = useState('all');

  // Extract all unique tags
  const allTags = useMemo(() => {
    const tagsSet = new Set();
    people.forEach(p => {
      (p.tags || []).forEach(t => tagsSet.add(t));
    });
    return Array.from(tagsSet);
  }, [people]);

  // Filtered people
  const filteredPeople = useMemo(() => {
    return people.filter(p => {
      const matchesSearch = 
        !search ||
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        (p.notes_summary || '').toLowerCase().includes(search.toLowerCase()) ||
        (p.aliases || []).some(a => a.toLowerCase().includes(search.toLowerCase()));

      const matchesTag = 
        selectedTag === 'all' || 
        (p.tags || []).some(t => t.toLowerCase() === selectedTag.toLowerCase());

      return matchesSearch && matchesTag;
    });
  }, [people, search, selectedTag]);

  // Quick stats
  const totalInteractions = people.reduce((acc, p) => acc + (p.interaction_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header and CRM Stats Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-xl border border-cyan-500/20">
                <Users className="w-5 h-5" />
              </div>
              <h1 className="text-xl sm:text-2xl font-extrabold text-white tracking-tight">
                People & Social Network CRM
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Personal knowledge graph automatically built from your daily journal entries
            </p>
          </div>

          {/* Stat pills */}
          <div className="flex items-center gap-3">
            <div className="bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-center">
              <span className="text-xs text-slate-400 block font-medium">Tracked People</span>
              <span className="text-lg font-black text-white font-mono">{people.length}</span>
            </div>
            <div className="bg-slate-950 px-3 py-1.5 rounded-xl border border-slate-800 text-center">
              <span className="text-xs text-slate-400 block font-medium">Total Interactions</span>
              <span className="text-lg font-black text-cyan-400 font-mono">{totalInteractions}</span>
            </div>
          </div>
        </div>

        {/* Search & Tag Filter Bar */}
        <div className="mt-6 flex flex-col md:flex-row items-stretch md:items-center gap-3 pt-4 border-t border-slate-800/80">
          {/* Search box */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by name, facts, role, or keywords..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/70 transition"
            />
          </div>

          {/* Tags row */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0">
            <button
              onClick={() => setSelectedTag('all')}
              className={`text-xs px-3 py-1.5 rounded-xl font-medium transition shrink-0 ${
                selectedTag === 'all'
                  ? 'bg-cyan-600 text-white font-semibold'
                  : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              All ({people.length})
            </button>
            {allTags.map(tag => (
              <button
                key={tag}
                onClick={() => setSelectedTag(tag)}
                className={`text-xs px-3 py-1.5 rounded-xl font-medium transition shrink-0 capitalize ${
                  selectedTag === tag
                    ? 'bg-cyan-600 text-white font-semibold'
                    : 'bg-slate-950 text-slate-400 hover:text-white border border-slate-800'
                }`}
              >
                #{tag}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Directory Grid */}
      {filteredPeople.length === 0 ? (
        <div className="text-center py-16 bg-slate-900/40 border border-dashed border-slate-800 rounded-2xl">
          <Users className="w-10 h-10 text-slate-600 mx-auto mb-2 opacity-60" />
          <h3 className="text-sm font-bold text-slate-300">No contacts found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            {search || selectedTag !== 'all' 
              ? 'Try changing your search keywords or tag filter.' 
              : 'Mention people and friends in your daily journal to automatically generate CRM profiles.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredPeople.map((person) => {
            const firstLetter = person.name ? person.name[0].toUpperCase() : 'P';

            return (
              <div
                key={person.id}
                onClick={() => onSelectPerson(person.id)}
                className="bg-slate-900/90 border border-slate-800 hover:border-cyan-500/50 rounded-2xl p-5 shadow-lg transition-all cursor-pointer group flex flex-col justify-between"
              >
                <div>
                  {/* Top row */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-500 p-[1.5px] shadow-md shadow-cyan-950/50">
                        <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center font-bold text-white text-base">
                          {firstLetter}
                        </div>
                      </div>
                      <div>
                        <h3 className="text-sm font-extrabold text-white group-hover:text-cyan-300 transition">
                          {person.name}
                        </h3>
                        {person.aliases && person.aliases.length > 1 && (
                          <p className="text-[11px] text-slate-500">
                            aka {person.aliases.filter(a => a.toLowerCase() !== person.name.toLowerCase()).join(', ')}
                          </p>
                        )}
                      </div>
                    </div>

                    <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 font-bold shrink-0">
                      {person.interaction_count} {person.interaction_count === 1 ? 'touch' : 'touches'}
                    </span>
                  </div>

                  {/* Facts / Summary snippet */}
                  <div className="mt-4 text-xs text-slate-300 space-y-1 bg-slate-950/60 p-3 rounded-xl border border-slate-800/80 min-h-[60px]">
                    {person.notes_summary ? (
                      <p className="line-clamp-3 leading-relaxed whitespace-pre-line text-[11px]">
                        {person.notes_summary}
                      </p>
                    ) : (
                      <p className="text-slate-600 italic text-[11px]">No facts recorded yet</p>
                    )}
                  </div>
                </div>

                {/* Bottom row: Dates & Tags */}
                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                  <div className="flex items-center gap-1.5 text-slate-400">
                    <Clock className="w-3 h-3 text-slate-500" />
                    <span>Last: <strong className="text-slate-200">{person.last_seen_date || 'N/A'}</strong></span>
                  </div>

                  <div className="flex items-center gap-1 text-cyan-400 font-bold group-hover:translate-x-0.5 transition">
                    <span>View Profile</span>
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
