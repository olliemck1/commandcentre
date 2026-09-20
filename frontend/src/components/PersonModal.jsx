import React, { useState, useEffect } from 'react';
import { 
  X, 
  Users, 
  Calendar, 
  Clock, 
  MapPin, 
  Edit3, 
  Trash2, 
  Save, 
  Sparkles, 
  Tag, 
  CheckCircle,
  MessageSquare
} from 'lucide-react';
import { fetchPersonDetail, updatePerson, deletePerson } from '../api/client';
import { formatDisplayDate } from '../utils/dateUtils';

export default function PersonModal({ personId, onClose, onUpdated, onDeleted }) {
  const [person, setPerson] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [notes, setNotes] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    if (!personId) return;
    loadPerson();
  }, [personId]);

  const loadPerson = async () => {
    setLoading(true);
    try {
      const data = await fetchPersonDetail(personId);
      setPerson(data);
      setNotes(data.notes_summary || '');
      setTagsInput((data.tags || []).join(', '));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const tagsArray = tagsInput
        .split(',')
        .map(t => t.trim())
        .filter(Boolean);

      const updated = await updatePerson(personId, {
        notes_summary: notes,
        tags: tagsArray
      });
      setPerson(updated);
      setIsEditing(false);
      if (onUpdated) onUpdated(updated);
    } catch (err) {
      alert(`Error saving: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to remove ${person?.name} from CRM?`)) return;
    try {
      await deletePerson(personId);
      if (onDeleted) onDeleted(personId);
      onClose();
    } catch (err) {
      alert(`Error deleting: ${err.message}`);
    }
  };

  if (!personId) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
      <div 
        className="bg-slate-900 border border-slate-800 rounded-3xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Top Header */}
        <div className="p-6 border-b border-slate-800/80 flex items-start justify-between bg-slate-950/40">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-600 to-blue-500 p-[2px] shadow-lg shadow-cyan-950/50">
              <div className="w-full h-full bg-slate-950 rounded-[14px] flex items-center justify-center text-xl font-black text-cyan-300">
                {person?.name ? person.name[0].toUpperCase() : 'P'}
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-extrabold text-white tracking-tight">
                  {person?.name || 'Loading profile...'}
                </h2>
                <span className="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  {person?.interaction_count || 0} interactions
                </span>
              </div>
              
              <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-slate-400">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5 text-slate-500" />
                  Met: <strong className="text-slate-200">{person?.first_met_date || 'N/A'}</strong>
                </span>
                <span className="text-slate-600">•</span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  Last Seen: <strong className="text-slate-200">{person?.last_seen_date || 'N/A'}</strong>
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleDelete}
              className="p-2 text-slate-500 hover:text-rose-400 rounded-xl hover:bg-rose-950/30 transition"
              title="Delete Contact"
            >
              <Trash2 className="w-4 h-4" />
            </button>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
              title="Close modal"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-16 text-center text-slate-500 text-xs">
              Loading profile details...
            </div>
          ) : (
            <>
              {/* Known Facts & Profile Summary */}
              <div className="bg-slate-950/80 border border-slate-800/90 rounded-2xl p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-cyan-400" />
                    <span className="text-xs font-bold text-white uppercase tracking-wider">
                      Learned Facts & Preferences
                    </span>
                  </div>

                  {!isEditing ? (
                    <button
                      onClick={() => setIsEditing(true)}
                      className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
                    >
                      <Edit3 className="w-3 h-3" />
                      Edit Notes
                    </button>
                  ) : (
                    <button
                      onClick={handleSave}
                      disabled={saving}
                      className="text-xs bg-cyan-600 hover:bg-cyan-500 text-white px-2.5 py-1 rounded-lg font-bold flex items-center gap-1"
                    >
                      <Save className="w-3 h-3" />
                      {saving ? 'Saving...' : 'Done'}
                    </button>
                  )}
                </div>

                {isEditing ? (
                  <div className="space-y-2">
                    <textarea
                      rows={4}
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 leading-relaxed font-mono"
                      placeholder="Bullet points of facts, coffee orders, projects, hobbies..."
                    />
                    <div>
                      <label className="text-[11px] text-slate-400 block mb-1">Tags (comma separated):</label>
                      <input
                        type="text"
                        value={tagsInput}
                        onChange={(e) => setTagsInput(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                        placeholder="colleague, coffee, mentor, runner"
                      />
                    </div>
                  </div>
                ) : (
                  <div>
                    {person?.notes_summary ? (
                      <div className="text-xs text-slate-200 leading-relaxed whitespace-pre-line space-y-1">
                        {person.notes_summary}
                      </div>
                    ) : (
                      <p className="text-xs text-slate-500 italic">No notes or facts logged yet.</p>
                    )}

                    {/* Tag chips */}
                    <div className="flex flex-wrap gap-1.5 mt-3 pt-2 border-t border-slate-800">
                      {(person?.tags || []).map((t, idx) => (
                        <span 
                          key={idx} 
                          className="text-[10px] px-2 py-0.5 rounded-full bg-slate-900 text-cyan-300 border border-cyan-500/20 font-mono"
                        >
                          #{t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Reverse Chronological Interaction History */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider">
                    Interaction Timeline ({person?.interactions?.length || 0})
                  </h3>
                </div>

                {person?.interactions?.length === 0 ? (
                  <p className="text-xs text-slate-500 italic py-4 text-center">No interactions recorded.</p>
                ) : (
                  <div className="relative pl-6 space-y-4 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                    {person.interactions.map((interaction) => (
                      <div key={interaction.id} className="relative group">
                        <div className="absolute -left-6 top-1.5 w-4 h-4 rounded-full bg-slate-950 border-2 border-cyan-500 flex items-center justify-center">
                          <div className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
                        </div>

                        <div className="bg-slate-950/70 border border-slate-800/80 rounded-xl p-3.5 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="font-mono text-xs font-bold text-cyan-400">
                              {interaction.date}
                            </span>
                            <div className="flex items-center gap-2">
                              {interaction.location && (
                                <span className="flex items-center gap-1 text-[10px] text-slate-400 px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800">
                                  <MapPin className="w-2.5 h-2.5 text-slate-500" />
                                  {interaction.location}
                                </span>
                              )}
                              <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-400 capitalize">
                                {interaction.sentiment}
                              </span>
                            </div>
                          </div>

                          <p className="text-xs text-slate-300 italic leading-relaxed">
                            "{interaction.context_snippet}"
                          </p>

                          {interaction.extracted_facts?.length > 0 && (
                            <div className="pt-1 border-t border-slate-900 space-y-1">
                              {interaction.extracted_facts.map((fact, fIdx) => (
                                <div key={fIdx} className="text-[11px] text-cyan-200/90 flex items-start gap-1">
                                  <span className="text-cyan-400 font-bold">•</span>
                                  <span>{fact}</span>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
