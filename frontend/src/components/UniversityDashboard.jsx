import React, { useState, useEffect, useMemo } from 'react';
import { 
  Sparkles, 
  Calendar as CalendarIcon, 
  Layers, 
  Clock, 
  CheckCircle2, 
  AlertTriangle, 
  BookOpen, 
  Plus, 
  RefreshCw, 
  Search, 
  Trash2, 
  ExternalLink, 
  X, 
  ChevronLeft, 
  ChevronRight, 
  MapPin, 
  Database, 
  GraduationCap, 
  Check, 
  Tag,
  Inbox
} from 'lucide-react';
import { 
  syncTimetableIcal, 
  syncTimetableMongo, 
  updateTimetableEvent, 
  deleteTimetableEvent, 
  createAssignment,
  updateAssignment,
  deleteAssignment,
  createModule
} from '../api/client';

export default function UniversityDashboard({
  modules = [],
  deadlines = [],
  tasks = [],
  timetableEvents = [],
  timetableStatus = null,
  onRefreshData,
  onShowToast
}) {
  // Deadlines & Tasks Hub Active Tab
  const [activeTab, setActiveTab] = useState('upcoming'); // 'upcoming' | 'all' | 'blackboard' | 'mytimetable' | 'manual' | 'completed'
  const [searchQuery, setSearchQuery] = useState('');
  const [deletingId, setDeletingId] = useState(null);

  // Syncing States
  const [isSyncing, setIsSyncing] = useState(false);
  const [isImportingMongo, setIsImportingMongo] = useState(false);

  // Modals
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [showModulesModal, setShowModulesModal] = useState(false);
  const [showAddModuleModal, setShowAddModuleModal] = useState(false);

  // New Deliverable Form State
  const [newTitle, setNewTitle] = useState('');
  const [newSubject, setNewSubject] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newPriority, setNewPriority] = useState('Medium');
  const [newSource, setNewSource] = useState('manual');
  const [newResourceLink, setNewResourceLink] = useState('');

  // New Module Form State
  const [newModCode, setNewModCode] = useState('');
  const [newModTitle, setNewModTitle] = useState('');
  const [newModCredits, setNewModCredits] = useState(20);
  const [newModTerm, setNewModTerm] = useState('Michaelmas / Epiphany');
  const [newModColor, setNewModColor] = useState('#6366f1');

  // Clock
  const [currentTime, setCurrentTime] = useState(new Date());
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Unified Deliverables List (863+ items)
  const deliverables = useMemo(() => {
    return timetableEvents.map((e) => {
      const start = e.start_time || e.startDate;
      const end = e.end_time || e.endDate || start;
      const due = e.dueDate || end || start;
      const displayStatus = (e.status === 'Completed' || e.status === 'submitted' || e.status === 'graded') 
        ? 'Completed' 
        : 'Not Started';

      return {
        _id: String(e.id || e.sync_id),
        id: e.id,
        syncId: e.sync_id || e.syncId,
        title: e.title,
        subject: e.subject || e.location || 'University',
        location: e.location || e.subject || '',
        startDate: start,
        endDate: end,
        dueDate: due,
        source: e.source || 'mytimetable',
        priority: e.priority || 'Medium',
        status: displayStatus,
        resourceLink: e.resourceLink || '',
        module_code: e.module_code,
        module_color: e.module_color || '#6366f1',
        module_title: e.module_title,
        event_type: e.event_type || 'lecture',
        description: e.description || ''
      };
    });
  }, [timetableEvents]);

  // Calendar State
  const [calendarDate, setCalendarDate] = useState(() => {
    const now = new Date();
    const upcoming = timetableEvents.find(e => new Date(e.start_time || e.startDate) >= now);
    if (upcoming) {
      return new Date(upcoming.start_time || upcoming.startDate);
    }
    return now;
  });
  const [calendarView, setCalendarView] = useState('day'); // 'day' | 'month' | 'week' | 'agenda'

  useEffect(() => {
    if (timetableEvents.length > 0) {
      const now = new Date();
      const upcoming = timetableEvents.find(e => new Date(e.start_time || e.startDate) >= now);
      if (upcoming) {
        setCalendarDate(new Date(upcoming.start_time || upcoming.startDate));
      }
    }
  }, [timetableEvents.length]);

  // KPI Calculations
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const inSevenDays = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);

  const upcomingCount = useMemo(() => {
    return deliverables.filter((item) => {
      if (item.status === 'Completed' || !item.dueDate) return false;
      const due = new Date(item.dueDate);
      return due >= today && due <= inSevenDays;
    }).length;
  }, [deliverables, today, inSevenDays]);

  const highPriorityCount = useMemo(() => {
    return deliverables.filter((item) => {
      return item.status !== 'Completed' && (item.priority || '').toLowerCase() === 'high';
    }).length;
  }, [deliverables]);

  const completedCount = useMemo(() => {
    return deliverables.filter((item) => item.status === 'Completed').length;
  }, [deliverables]);

  const activeCount = useMemo(() => {
    return deliverables.filter((item) => item.status !== 'Completed').length;
  }, [deliverables]);

  // Due Status Formatter (Matching Personal Dashboard)
  const getDueStatus = (dueDateString, isCompleted) => {
    if (!dueDateString) return null;
    const due = new Date(dueDateString);
    if (isNaN(due.getTime())) return null;

    const target = new Date(due.getFullYear(), due.getMonth(), due.getDate());
    const diffDays = Math.round((target - today) / (1000 * 60 * 60 * 24));

    if (isCompleted) {
      return {
        text: `Due ${due.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`,
        className: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
      };
    }

    if (diffDays < 0) {
      return {
        text: `${Math.abs(diffDays)}d Overdue`,
        className: 'bg-rose-500/10 text-rose-400 border border-rose-500/30 font-bold'
      };
    } else if (diffDays === 0) {
      return {
        text: 'Due Today',
        className: 'bg-rose-500/15 text-rose-300 border border-rose-500/40 font-bold animate-pulse'
      };
    } else if (diffDays === 1) {
      return {
        text: 'Due Tomorrow',
        className: 'bg-amber-500/10 text-amber-300 border border-amber-500/30 font-semibold'
      };
    } else if (diffDays <= 7) {
      return {
        text: `Due in ${diffDays} days`,
        className: 'bg-amber-500/10 text-amber-300 border border-amber-500/30 font-medium'
      };
    } else {
      return {
        text: `Due ${due.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`,
        className: 'bg-slate-800/80 text-slate-300 border border-slate-700'
      };
    }
  };

  // Filtered Deliverables (Shows the 292 upcoming sessions under Upcoming tab!)
  const filteredDeliverables = useMemo(() => {
    return deliverables.filter((item) => {
      // Search match
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const titleMatch = (item.title || '').toLowerCase().includes(q);
        const subjectMatch = (item.subject || '').toLowerCase().includes(q);
        const modMatch = (item.module_code || '').toLowerCase().includes(q);
        if (!titleMatch && !subjectMatch && !modMatch) return false;
      }

      const isCompleted = item.status === 'Completed';

      switch (activeTab) {
        case 'upcoming':
          if (isCompleted) return false;
          if (item.dueDate) {
            const due = new Date(item.dueDate);
            return due >= today;
          }
          return true;

        case 'completed':
          return isCompleted;

        case 'blackboard':
          return (item.source || '').toLowerCase() === 'blackboard';

        case 'mytimetable':
          return (item.source || '').toLowerCase() === 'mytimetable';

        case 'manual':
          return (item.source || '').toLowerCase() === 'manual' || !item.source;

        case 'all':
        default:
          return true;
      }
    }).sort((a, b) => {
      const dateA = new Date(a.dueDate || a.startDate || 0).getTime();
      const dateB = new Date(b.dueDate || b.startDate || 0).getTime();
      return dateA - dateB;
    });
  }, [deliverables, searchQuery, activeTab, today]);

  // Handlers
  const handleToggleStatus = async (item) => {
    const nextStatus = item.status === 'Completed' ? 'Not Started' : 'Completed';
    try {
      if (item.id) {
        await updateTimetableEvent(item.id, { status: nextStatus });
      } else {
        await updateAssignment(item._id, { status: nextStatus });
      }
      if (onRefreshData) onRefreshData();
      if (onShowToast) onShowToast(`Marked as ${nextStatus}`);
    } catch (err) {
      alert(`Failed to update status: ${err.message}`);
    }
  };

  const handleDeleteItem = async (item) => {
    if (!window.confirm(`Delete "${item.title}" from your workspace?`)) return;
    setDeletingId(item._id);
    try {
      if (item.id) {
        await deleteTimetableEvent(item.id);
      } else {
        await deleteAssignment(item._id);
      }
      if (onRefreshData) onRefreshData();
      if (onShowToast) onShowToast('Item deleted');
    } catch (err) {
      alert(`Failed to delete item: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handleSyncFeeds = async () => {
    setIsSyncing(true);
    try {
      const res = await syncTimetableIcal();
      if (onRefreshData) await onRefreshData();
      if (onShowToast) onShowToast(`Durham feeds synced: ${res.total_processed} items processed!`);
    } catch (err) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
  };

  const handleImportMongo = async () => {
    setIsImportingMongo(true);
    try {
      const res = await syncTimetableMongo();
      if (onRefreshData) await onRefreshData();
      if (onShowToast) onShowToast(`MongoDB import complete: ${res.total_processed} deliverables loaded!`);
    } catch (err) {
      alert(`MongoDB import failed: ${err.message}`);
    } finally {
      setIsImportingMongo(false);
    }
  };

  const handleCreateDeliverableSubmit = async (e) => {
    e.preventDefault();
    if (!newTitle.trim() || !newDueDate) return;

    try {
      await createAssignment({
        title: newTitle.trim(),
        subject: newSubject.trim() || 'University',
        dueDate: newDueDate,
        startDate: newDueDate,
        endDate: newDueDate,
        priority: newPriority,
        source: newSource,
        resourceLink: newResourceLink.trim()
      });
      setIsFormOpen(false);
      setNewTitle('');
      setNewSubject('');
      setNewDueDate('');
      setNewResourceLink('');
      if (onRefreshData) await onRefreshData();
      if (onShowToast) onShowToast('Deliverable added successfully!');
    } catch (err) {
      alert(`Failed to create deliverable: ${err.message}`);
    }
  };

  const handleCreateModuleSubmit = async (e) => {
    e.preventDefault();
    if (!newModCode.trim() || !newModTitle.trim()) return;

    try {
      await createModule({
        code: newModCode.trim().toUpperCase(),
        title: newModTitle.trim(),
        credits: parseInt(newModCredits) || 20,
        term: newModTerm.trim(),
        color: newModColor
      });
      setShowAddModuleModal(false);
      setNewModCode('');
      setNewModTitle('');
      if (onRefreshData) await onRefreshData();
      if (onShowToast) onShowToast(`Module ${newModCode.toUpperCase()} registered!`);
    } catch (err) {
      alert(`Failed to create module: ${err.message}`);
    }
  };

  // Calendar Calculations
  const calYear = calendarDate.getFullYear();
  const calMonth = calendarDate.getMonth();

  const handlePrevMonth = () => {
    if (calendarView === 'day') {
      const d = new Date(calendarDate); d.setDate(d.getDate() - 1); setCalendarDate(d);
    } else { setCalendarDate(new Date(calYear, calMonth - 1, 1)); }
  };
  const handleNextMonth = () => {
    if (calendarView === 'day') {
      const d = new Date(calendarDate); d.setDate(d.getDate() + 1); setCalendarDate(d);
    } else { setCalendarDate(new Date(calYear, calMonth + 1, 1)); }
  };
  const handleToday = () => {
    setCalendarDate(new Date());
  };

  // Generate Month Days Grid (Monday first)
  const calendarGrid = useMemo(() => {
    const firstDayOfMonth = new Date(calYear, calMonth, 1);
    const lastDayOfMonth = new Date(calYear, calMonth + 1, 0);

    const startDayOfWeek = (firstDayOfMonth.getDay() + 6) % 7;
    const days = [];

    const prevMonthLastDay = new Date(calYear, calMonth, 0).getDate();
    for (let i = startDayOfWeek - 1; i >= 0; i--) {
      days.push({
        date: new Date(calYear, calMonth - 1, prevMonthLastDay - i),
        isCurrentMonth: false
      });
    }

    for (let d = 1; d <= lastDayOfMonth.getDate(); d++) {
      days.push({
        date: new Date(calYear, calMonth, d),
        isCurrentMonth: true
      });
    }

    const remaining = (7 - (days.length % 7)) % 7;
    for (let i = 1; i <= remaining; i++) {
      days.push({
        date: new Date(calYear, calMonth + 1, i),
        isCurrentMonth: false
      });
    }

    return days;
  }, [calYear, calMonth]);

  const eventsByDate = useMemo(() => {
    const map = {};
    deliverables.forEach((item) => {
      const dateStr = (item.startDate || item.dueDate || '').slice(0, 10);
      if (dateStr) {
        if (!map[dateStr]) map[dateStr] = [];
        map[dateStr].push(item);
      }
    });
    return map;
  }, [deliverables]);

  return (
    <div className="space-y-6">
      {/* 1. EXECUTIVE HEADER */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl">
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-indigo-600 to-indigo-800 flex items-center justify-center text-white shadow-lg shadow-indigo-950/60 shrink-0">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h1 className="text-xl font-extrabold text-white tracking-tight">
                Academic & Focus Hub
              </h1>
              <span className="text-[10px] font-mono font-bold px-2.5 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/60">
                Durham University
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Personal Command Center • Live Timetable, Blackboard Deliverables & Degree Modules
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Live Date and Clock */}
          <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 px-3 py-1.5 rounded-xl font-mono text-xs text-slate-300">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
            <span>
              {currentTime.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })}
              {' • '}
              {currentTime.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>

          {/* Sync Feeds Action */}
          <button
            onClick={handleSyncFeeds}
            disabled={isSyncing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition active:scale-95 disabled:opacity-50"
            title="Sync Blackboard and Timetable .ics feeds"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-indigo-400 ${isSyncing ? 'animate-spin' : ''}`} />
            <span>{isSyncing ? 'Syncing...' : 'Sync'}</span>
          </button>

          {/* Import MongoDB */}
          <button
            onClick={handleImportMongo}
            disabled={isImportingMongo}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-950/40 hover:bg-emerald-900/40 text-emerald-300 text-xs font-semibold border border-emerald-800/50 transition active:scale-95 disabled:opacity-50"
            title="Pull fresh deliverables directly from MongoDB cluster"
          >
            <Database className={`w-3.5 h-3.5 text-emerald-400 ${isImportingMongo ? 'animate-spin' : ''}`} />
            <span>{isImportingMongo ? 'Importing...' : 'Import Mongo'}</span>
          </button>

          {/* Degree Modules Toggle */}
          <button
            onClick={() => setShowModulesModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950 hover:bg-slate-800 text-slate-300 text-xs font-semibold border border-slate-800 transition"
          >
            <GraduationCap className="w-3.5 h-3.5 text-indigo-400" />
            <span>Modules ({modules.length})</span>
          </button>

          {/* Add Assignment/Task Action */}
          <button
            onClick={() => setIsFormOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white text-xs font-bold shadow-lg shadow-indigo-950/50 transition active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>+ Task</span>
          </button>
        </div>
      </header>

      {/* 2. TOP KPI METRICS ROW */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Due in 7 Days */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-lg flex items-center gap-4 relative overflow-hidden group hover:border-rose-500/40 transition">
          <div className="w-11 h-11 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/20 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Due in 7 Days</span>
            <span className="text-2xl font-black text-white">{upcomingCount}</span>
            <span className="text-[11px] text-slate-400 block mt-0.5">Immediate focus required</span>
          </div>
        </div>

        {/* High Priority */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-lg flex items-center gap-4 relative overflow-hidden group hover:border-amber-500/40 transition">
          <div className="w-11 h-11 rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center shrink-0">
            <Clock className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">High Priority</span>
            <span className="text-2xl font-black text-white">{highPriorityCount}</span>
            <span className="text-[11px] text-slate-400 block mt-0.5">Critical assignments</span>
          </div>
        </div>

        {/* Active Tasks (Displays the 292 upcoming tasks!) */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-lg flex items-center gap-4 relative overflow-hidden group hover:border-indigo-500/40 transition">
          <div className="w-11 h-11 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center justify-center shrink-0">
            <BookOpen className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Active Tasks</span>
            <span className="text-2xl font-black text-white">{activeCount}</span>
            <span className="text-[11px] text-slate-400 block mt-0.5">{completedCount} tasks completed</span>
          </div>
        </div>

        {/* Completion */}
        <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-lg flex items-center gap-4 relative overflow-hidden group hover:border-emerald-500/40 transition">
          <div className="w-11 h-11 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center shrink-0">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">Completion</span>
            <span className="text-2xl font-black text-white">
              {deliverables.length > 0 ? `${Math.round((completedCount / deliverables.length) * 100)}%` : '100%'}
            </span>
            <span className="text-[11px] text-slate-400 block mt-0.5">{deliverables.length} total deliverables</span>
          </div>
        </div>
      </section>

      {/* 3. MAIN TWO-COLUMN DASHBOARD GRID */}
      <main className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: Academic Schedule Calendar Widget (lg:col-span-7) */}
        <section className="lg:col-span-7 bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <CalendarIcon className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-bold text-white tracking-tight">Academic Schedule</h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                Live Sync
              </span>
            </div>
          </div>

          {/* Calendar Toolbar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950 p-2.5 rounded-xl border border-slate-800">
            <div className="flex items-center gap-1.5">
              <button
                onClick={handlePrevMonth}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white transition"
                title="Previous Month"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <button
                onClick={handleToday}
                className="px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-semibold text-slate-300 hover:text-white transition"
              >
                Today
              </button>
              <button
                onClick={handleNextMonth}
                className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white transition"
                title="Next Month"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs font-bold text-white font-mono uppercase tracking-wider">
              {calendarView === 'day'
                ? calendarDate.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
                : calendarDate.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}
            </div>

            <div className="flex items-center gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
              {['day', 'month', 'week', 'agenda'].map((v) => (
                <button
                  key={v}
                  onClick={() => setCalendarView(v)}
                  className={`px-2.5 py-1 rounded text-xs font-semibold capitalize transition ${
                    calendarView === v ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          {/* Day View */}
          {calendarView === 'day' && (() => {
            const calDateStr = (() => {
              const y = calendarDate.getFullYear();
              const m = String(calendarDate.getMonth() + 1).padStart(2, '0');
              const d = String(calendarDate.getDate()).padStart(2, '0');
              return `${y}-${m}-${d}`;
            })();
            const todayStr = (() => {
              const n = new Date();
              const y = n.getFullYear();
              const m = String(n.getMonth() + 1).padStart(2, '0');
              const d = String(n.getDate()).padStart(2, '0');
              return `${y}-${m}-${d}`;
            })();

            const dayItems = deliverables
              .filter(item => {
                const d = item.startDate || item.dueDate;
                return d && d.slice(0, 10) === calDateStr;
              })
              .sort((a, b) => {
                const tA = new Date(a.startDate || a.dueDate).getTime();
                const tB = new Date(b.startDate || b.dueDate).getTime();
                return tA - tB;
              });

            // Find next day that has events if today is empty
            let nextEventDate = null;
            if (dayItems.length === 0) {
              const futureDates = deliverables
                .map(item => (item.startDate || item.dueDate || '').slice(0, 10))
                .filter(d => d && d > calDateStr)
                .sort();
              if (futureDates.length > 0) nextEventDate = futureDates[0];
            }

            const isToday = calDateStr === todayStr;

            return (
              <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
                {dayItems.length === 0 ? (
                  <div className="text-center py-10 border border-dashed border-slate-800 rounded-xl space-y-3">
                    <CalendarIcon className="w-8 h-8 text-slate-600 mx-auto opacity-40" />
                    <p className="text-xs font-semibold text-slate-400">
                      {isToday ? 'No sessions today' : 'No sessions on this day'}
                    </p>
                    {nextEventDate && (
                      <button
                        onClick={() => {
                          const [y, m, d] = nextEventDate.split('-').map(Number);
                          setCalendarDate(new Date(y, m - 1, d, 12, 0, 0));
                        }}
                        className="text-[11px] font-bold text-indigo-400 hover:text-indigo-300 transition flex items-center gap-1 mx-auto"
                      >
                        <ChevronRight className="w-3.5 h-3.5" />
                        Jump to {(() => {
                          const [y, m, d] = nextEventDate.split('-').map(Number);
                          return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
                        })()}
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="relative pl-6 space-y-3 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
                    {dayItems.map(item => {
                      const start = item.startDate ? new Date(item.startDate) : null;
                      const end = item.endDate ? new Date(item.endDate) : null;
                      const timeLabel = start
                        ? start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : null;
                      const endLabel = end && end.getTime() !== (start ? start.getTime() : 0)
                        ? end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                        : null;
                      const isBlackboard = item.source === 'blackboard';

                      return (
                        <div
                          key={item._id}
                          onClick={() => setSelectedEvent(item)}
                          className="relative group cursor-pointer"
                        >
                          {/* Timeline dot */}
                          <div className={`absolute -left-6 top-3.5 w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                            isBlackboard ? 'bg-amber-950 border-amber-500' : 'bg-indigo-950 border-indigo-500'
                          }`}>
                            <div className={`w-1.5 h-1.5 rounded-full ${isBlackboard ? 'bg-amber-400' : 'bg-indigo-400'}`} />
                          </div>

                          <div className="bg-slate-950/80 border border-slate-800 hover:border-indigo-500/60 rounded-xl p-3.5 transition space-y-2">
                            {/* Time + Module badge + Type chip */}
                            <div className="flex items-center justify-between gap-2 flex-wrap">
                              <div className="flex items-center gap-2">
                                {timeLabel && (
                                  <span className="font-mono text-[11px] font-bold text-white bg-slate-900 border border-slate-700 px-1.5 py-0.5 rounded">
                                    {timeLabel}{endLabel ? ` \u2192 ${endLabel}` : ''}
                                  </span>
                                )}
                                {item.module_code && (
                                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                                    {item.module_code}
                                  </span>
                                )}
                              </div>
                              <span className={`text-[9px] uppercase font-mono font-bold px-2 py-0.5 rounded border ${
                                isBlackboard
                                  ? 'bg-amber-500/10 text-amber-300 border-amber-500/20'
                                  : 'bg-slate-800/80 text-slate-400 border-slate-700'
                              }`}>
                                {item.event_type || item.source || 'session'}
                              </span>
                            </div>

                            {/* Title */}
                            <p className="text-xs font-bold text-white leading-tight">
                              {item.title}
                            </p>

                            {/* Location */}
                            {item.location && (
                              <div className="flex items-center gap-1.5 text-[11px]">
                                <MapPin className="w-3 h-3 text-emerald-400 shrink-0" />
                                <span className="font-semibold text-emerald-300">{item.location}</span>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })()}

          {/* Month View Grid */}
          {calendarView === 'month' && (
            <div className="space-y-1">
              {/* Day of week headers */}
              <div className="grid grid-cols-7 gap-1 text-center font-mono text-[11px] font-bold text-slate-500 py-1">
                {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
                  <div key={d}>{d}</div>
                ))}
              </div>

              {/* Grid cells */}
              <div className="grid grid-cols-7 gap-1">
                {calendarGrid.map((item, idx) => {
                  const dateStr = item.date.toISOString().slice(0, 10);
                  const isToday = dateStr === today.toISOString().slice(0, 10);
                  const dayEvents = eventsByDate[dateStr] || [];

                  return (
                    <div
                      key={idx}
                      onClick={() => {
                        if (dayEvents.length > 0) {
                          setSelectedEvent(dayEvents[0]);
                        }
                      }}
                      className={`min-h-[85px] p-1.5 rounded-xl border transition-all flex flex-col justify-between ${
                        item.isCurrentMonth
                          ? 'bg-slate-950/80 border-slate-800 hover:border-slate-700'
                          : 'bg-slate-950/30 border-slate-900/60 opacity-40'
                      } ${isToday ? 'ring-1 ring-indigo-500/80 border-indigo-500/50 bg-indigo-950/20' : ''}`}
                    >
                      <div className="flex items-center justify-between">
                        <span
                          className={`text-[11px] font-mono font-bold ${
                            isToday ? 'text-indigo-400 font-extrabold' : item.isCurrentMonth ? 'text-slate-300' : 'text-slate-600'
                          }`}
                        >
                          {item.date.getDate()}
                        </span>
                        {dayEvents.length > 0 && (
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
                        )}
                      </div>

                      {/* Event pills for day */}
                      <div className="space-y-1 mt-1 overflow-hidden">
                        {dayEvents.slice(0, 2).map((ev) => (
                          <div
                            key={ev._id}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelectedEvent(ev);
                            }}
                            className={`text-[9px] truncate px-1 py-0.5 rounded font-medium cursor-pointer transition ${
                              ev.source === 'blackboard'
                                ? 'bg-amber-500/20 text-amber-300 hover:bg-amber-500/30'
                                : ev.priority === 'High'
                                ? 'bg-rose-500/20 text-rose-300 hover:bg-rose-500/30'
                                : 'bg-indigo-500/20 text-indigo-300 hover:bg-indigo-500/30'
                            }`}
                            title={ev.title}
                          >
                            {ev.module_code ? `[${ev.module_code}] ` : ''}{ev.title}
                          </div>
                        ))}
                        {dayEvents.length > 2 && (
                          <div className="text-[9px] text-slate-500 font-mono text-center">
                            +{dayEvents.length - 2} more
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Week View */}
          {calendarView === 'week' && (
            <div className="space-y-2">
              <div className="text-xs text-slate-400 font-medium pb-1">
                Sessions scheduled for the selected week:
              </div>
              <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
                {deliverables
                  .filter(item => {
                    if (!item.startDate) return false;
                    const d = new Date(item.startDate);
                    const diff = Math.abs(d.getTime() - calendarDate.getTime()) / (1000 * 3600 * 24);
                    return diff <= 4;
                  })
                  .slice(0, 15)
                  .map(item => (
                    <div
                      key={item._id}
                      onClick={() => setSelectedEvent(item)}
                      className="p-3 bg-slate-950 border border-slate-800 hover:border-indigo-500/50 rounded-xl cursor-pointer transition flex items-center justify-between gap-3"
                    >
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300">
                            {item.module_code || 'UNI'}
                          </span>
                          <span className="text-xs font-bold text-white truncate max-w-[280px]">
                            {item.title}
                          </span>
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-2">
                          <Clock className="w-3 h-3 text-slate-500" />
                          <span>{new Date(item.startDate).toLocaleString([], { weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                          {item.location && (
                            <>
                              <span>•</span>
                              <span className="text-emerald-400 font-medium">Room: {item.location}</span>
                            </>
                          )}
                        </div>
                      </div>
                      <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                        {item.source}
                      </span>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Agenda View */}
          {calendarView === 'agenda' && (
            <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
              {deliverables.slice(0, 25).map(item => (
                <div
                  key={item._id}
                  onClick={() => setSelectedEvent(item)}
                  className="p-3 bg-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl cursor-pointer transition flex items-center justify-between gap-3"
                >
                  <div className="space-y-1">
                    <h3 className="text-xs font-bold text-white">{item.title}</h3>
                    <div className="text-[11px] text-slate-400 flex items-center gap-2 flex-wrap">
                      <span>{new Date(item.startDate || item.dueDate).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
                      {item.location && <span className="text-emerald-400 font-semibold">• {item.location}</span>}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                    {item.source}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* RIGHT COLUMN: Deadlines & Tasks Hub (lg:col-span-5) */}
        <section className="lg:col-span-5 bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              <h2 className="text-base font-bold text-white tracking-tight">Deadlines & Tasks</h2>
            </div>
            <button
              onClick={() => setIsFormOpen(true)}
              className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New</span>
            </button>
          </div>

          {/* 6 Tabs Switcher (Matching Personal Dashboard) */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
            {[
              { id: 'upcoming', label: 'Upcoming' },
              { id: 'all', label: 'All Tasks' },
              { id: 'blackboard', label: 'Blackboard' },
              { id: 'mytimetable', label: 'Timetable' },
              { id: 'manual', label: 'Personal' },
              { id: 'completed', label: 'Completed' }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition shrink-0 ${
                  activeTab === tab.id
                    ? 'bg-indigo-600 text-white shadow'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Live Search Bar */}
          <div className="relative">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search assignments or subjects..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
            />
          </div>

          {/* Deliverables List (Shows 292 upcoming sessions!) */}
          <div className="space-y-2.5 max-h-[560px] overflow-y-auto pr-1">
            {filteredDeliverables.length === 0 ? (
              <div className="text-center py-12 border border-dashed border-slate-800 rounded-xl space-y-2">
                <Inbox className="w-8 h-8 text-slate-600 mx-auto opacity-50" />
                <p className="text-xs font-semibold text-slate-400">No assignments or classes found</p>
                <span className="text-[11px] text-slate-500 block">
                  {searchQuery ? 'Try a different search keyword' : 'All caught up or try switching filter tabs!'}
                </span>
              </div>
            ) : (
              filteredDeliverables.map((item) => {
                const isDone = item.status === 'Completed';
                const dueStatus = getDueStatus(item.dueDate, isDone);
                const priorityLower = (item.priority || 'Medium').toLowerCase();

                return (
                  <div
                    key={item._id}
                    className={`bg-slate-950/90 border rounded-xl p-3.5 transition-all shadow-sm space-y-2.5 hover:border-slate-700 ${
                      isDone ? 'border-slate-800/60 opacity-60' : 'border-slate-800'
                    }`}
                  >
                    {/* Top Row: Checkbox + Title/Subject + Actions */}
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-2.5 flex-1 min-w-0">
                        {/* Circular status checkbox */}
                        <button
                          onClick={() => handleToggleStatus(item)}
                          className={`w-4 h-4 mt-0.5 rounded border flex items-center justify-center transition shrink-0 ${
                            isDone 
                              ? 'bg-emerald-600 border-emerald-500 text-white' 
                              : 'border-slate-600 hover:border-indigo-400 bg-slate-900'
                          }`}
                          title={isDone ? 'Mark as Incomplete' : 'Mark as Completed'}
                        >
                          {isDone && <Check className="w-3 h-3 stroke-[3]" />}
                        </button>

                        <div className="min-w-0 flex-1">
                          <h3 
                            className={`text-xs font-bold truncate leading-tight ${
                              isDone ? 'line-through text-slate-400' : 'text-white'
                            }`}
                            title={item.title}
                          >
                            {item.title}
                          </h3>
                          <div className="text-[11px] text-slate-400 truncate mt-0.5 flex items-center gap-1.5">
                            <span className="text-indigo-300 font-medium">{item.subject || 'University'}</span>
                            {item.location && item.location !== item.subject && (
                              <span className="text-emerald-400 font-medium">• Room: {item.location}</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Item Action Buttons */}
                      <div className="flex items-center gap-1 shrink-0">
                        {item.resourceLink && item.resourceLink.length > 3 && (
                          <a
                            href={item.resourceLink.startsWith('http') ? item.resourceLink : `https://${item.resourceLink}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1 text-slate-400 hover:text-indigo-400 rounded transition"
                            title="Open Resource Link"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                        <button
                          onClick={() => handleDeleteItem(item)}
                          disabled={deletingId === item._id}
                          className="p-1 text-slate-500 hover:text-rose-400 rounded transition"
                          title="Delete"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    {/* Bottom Row: Priority badge, Source badge, Due Date countdown badge */}
                    <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-900 text-[10px] flex-wrap">
                      <div className="flex items-center gap-1.5">
                        <span className={`px-2 py-0.5 rounded font-bold uppercase tracking-wider ${
                          priorityLower === 'high'
                            ? 'bg-rose-500/15 text-rose-300 border border-rose-500/30'
                            : priorityLower === 'low'
                            ? 'bg-slate-800 text-slate-400 border border-slate-700'
                            : 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                        }`}>
                          {item.priority || 'Medium'}
                        </span>

                        <span className="px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 font-mono">
                          {item.source || 'manual'}
                        </span>
                      </div>

                      {dueStatus && (
                        <span className={`px-2 py-0.5 rounded flex items-center gap-1 ${dueStatus.className}`}>
                          <Clock className="w-3 h-3" />
                          <span>{dueStatus.text}</span>
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>

      </main>

      {/* 4. MODALS */}

      {/* Add Deliverable/Task Modal */}
      {isFormOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Plus className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Create New Task / Deliverable</h3>
              </div>
              <button onClick={() => setIsFormOpen(false)} className="p-1 text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateDeliverableSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Title *</label>
                <input
                  type="text"
                  required
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. COMP2221 Coursework 1 or Lab Report"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-semibold mb-1">Subject / Room / Module</label>
                <input
                  type="text"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  placeholder="e.g. CLC202, COMP2221, or Algorithms"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-semibold mb-1">Due Date & Time *</label>
                <input
                  type="datetime-local"
                  required
                  value={newDueDate}
                  onChange={(e) => setNewDueDate(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Priority</label>
                  <select
                    value={newPriority}
                    onChange={(e) => setNewPriority(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="Low">Low</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Category / Source</label>
                  <select
                    value={newSource}
                    onChange={(e) => setNewSource(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="manual">Personal</option>
                    <option value="blackboard">Blackboard</option>
                    <option value="mytimetable">Timetable</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 font-semibold mb-1">Resource / Submission Link</label>
                <input
                  type="url"
                  value={newResourceLink}
                  onChange={(e) => setNewResourceLink(e.target.value)}
                  placeholder="https://blackboard.durham.ac.uk/..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsFormOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition shadow-lg shadow-indigo-950/50"
                >
                  Save Deliverable
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Event Details Slide-over / Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <CalendarIcon className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Session & Event Details</h3>
              </div>
              <button onClick={() => setSelectedEvent(null)} className="p-1 text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 font-semibold block">Title</span>
                <span className="text-sm font-bold text-white mt-0.5 block">{selectedEvent.title}</span>
              </div>

              <div className="grid grid-cols-2 gap-3 bg-slate-950 p-3 rounded-xl border border-slate-800">
                <div>
                  <span className="text-slate-400 font-semibold block">Scheduled Time</span>
                  <span className="text-slate-200 mt-0.5 block">
                    {new Date(selectedEvent.startDate || selectedEvent.dueDate).toLocaleString([], {
                      weekday: 'short',
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-semibold block">Classroom / Venue</span>
                  <span className="text-emerald-400 font-bold mt-0.5 flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" />
                    {selectedEvent.location || selectedEvent.subject || 'Campus'}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-semibold block">Data Source</span>
                  <span className="text-indigo-300 uppercase font-mono font-bold mt-0.5 block">
                    {selectedEvent.source}
                  </span>
                </div>

                <div>
                  <span className="text-slate-400 font-semibold block">Status</span>
                  <span className={`font-bold mt-0.5 block ${selectedEvent.status === 'Completed' ? 'text-emerald-400' : 'text-amber-400'}`}>
                    {selectedEvent.status}
                  </span>
                </div>
              </div>

              {selectedEvent.resourceLink && (
                <div>
                  <span className="text-slate-400 font-semibold block mb-1">Direct Link</span>
                  <a
                    href={selectedEvent.resourceLink.startsWith('http') ? selectedEvent.resourceLink : `https://${selectedEvent.resourceLink}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-950/60 text-indigo-300 border border-indigo-800/60 hover:text-white transition font-medium"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Open in Blackboard / Lecture Portal</span>
                  </a>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-3 border-t border-slate-800">
              <button
                onClick={() => {
                  handleToggleStatus(selectedEvent);
                  setSelectedEvent(null);
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition"
              >
                {selectedEvent.status === 'Completed' ? 'Mark as Incomplete' : 'Mark as Completed'}
              </button>

              <button
                onClick={() => setSelectedEvent(null)}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modules Overview Modal */}
      {showModulesModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl p-6 shadow-2xl space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Durham University Degree Modules</h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setShowAddModuleModal(true)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Module</span>
                </button>
                <button onClick={() => setShowModulesModal(false)} className="p-1 text-slate-400 hover:text-white">
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="text-xs text-slate-400">
              All 13 official Computer Science and Mathematics degree modules tracked in your command centre:
            </div>

            <div className="space-y-2.5 flex-1 overflow-y-auto pr-1">
              {modules.map((m) => (
                <div
                  key={m.id}
                  className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 flex items-center justify-between gap-4"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span
                        className="font-mono text-xs font-bold px-2 py-0.5 rounded"
                        style={{
                          backgroundColor: `${m.color || '#6366f1'}25`,
                          color: m.color || '#6366f1',
                          border: `1px solid ${m.color || '#6366f1'}50`
                        }}
                      >
                        {m.code}
                      </span>
                      <h4 className="text-xs font-bold text-white">{m.title}</h4>
                    </div>
                    <div className="text-[11px] text-slate-400 flex items-center gap-3">
                      <span>Term: {m.term || 'Academic Year'}</span>
                      <span>•</span>
                      <span>Credits: <strong>{m.credits || 20}</strong></span>
                      {m.pending_deadlines > 0 && (
                        <>
                          <span>•</span>
                          <span className="text-amber-400 font-semibold">{m.pending_deadlines} active tasks</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowModulesModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Module Modal */}
      {showAddModuleModal && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Register Degree Module</h3>
              </div>
              <button onClick={() => setShowAddModuleModal(false)} className="p-1 text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateModuleSubmit} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-400 font-semibold mb-1">Module Code *</label>
                <input
                  type="text"
                  required
                  value={newModCode}
                  onChange={(e) => setNewModCode(e.target.value)}
                  placeholder="e.g. COMP3001"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-slate-400 font-semibold mb-1">Module Title *</label>
                <input
                  type="text"
                  required
                  value={newModTitle}
                  onChange={(e) => setNewModTitle(e.target.value)}
                  placeholder="e.g. Advanced Computer Science"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Credits</label>
                  <input
                    type="number"
                    value={newModCredits}
                    onChange={(e) => setNewModCredits(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Color Tag</label>
                  <input
                    type="color"
                    value={newModColor}
                    onChange={(e) => setNewModColor(e.target.value)}
                    className="w-full h-9 bg-slate-950 border border-slate-800 rounded-xl px-1 py-1 cursor-pointer"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModuleModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition"
                >
                  Register Module
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
