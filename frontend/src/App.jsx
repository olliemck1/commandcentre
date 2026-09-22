import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import DateNavigator from './components/DateNavigator';
import SummaryCards from './components/SummaryCards';
import JournalEditor from './components/JournalEditor';
import DailyTimeline from './components/DailyTimeline';
import PeopleDirectory from './components/PeopleDirectory';
import PersonModal from './components/PersonModal';
import SettingsModal from './components/SettingsModal';
import UniversityDashboard from './components/UniversityDashboard';
import ChatAssistant from './components/ChatAssistant';
import LockScreen from './components/LockScreen';

import { 
  fetchAuthStatus,
  verifyAuthToken,
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  fetchDailyMetrics, 
  syncGarmin, 
  fetchGarminStatus, 
  fetchJournalEntriesForDate, 
  submitJournalEntry, 
  deleteJournalEntry, 
  fetchPeople,
  fetchModules,
  fetchDeadlines,
  fetchAcademicTasks,
  fetchTimetable,
  fetchTimetableStatus
} from './api/client';
import { getTodayString } from './utils/dateUtils';
import { CheckCircle2, AlertTriangle, X, Menu, Search, Bot, LayoutDashboard, GraduationCap, Users } from 'lucide-react';

export default function App() {
  const [selectedDate, setSelectedDate] = useState(getTodayString());
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Tabbed routing with hash support
  const getInitialTab = () => {
    const hash = window.location.hash.replace('#', '').toLowerCase();
    if (['daily', 'uni', 'people', 'chat', 'settings'].includes(hash)) return hash;
    return 'daily';
  };

  const [activeTab, setActiveTab] = useState(getInitialTab);
  const [workspace, setWorkspace] = useState(() => activeTab === 'uni' ? 'uni' : 'life');

  // Update hash when activeTab changes
  useEffect(() => {
    window.location.hash = activeTab;
    if (activeTab === 'uni') setWorkspace('uni');
    if (activeTab === 'daily') setWorkspace('life');
  }, [activeTab]);

  // Data state
  const [metrics, setMetrics] = useState(null);
  const [journalEntries, setJournalEntries] = useState([]);
  const [people, setPeople] = useState([]);
  const [modules, setModules] = useState([]);
  const [deadlines, setDeadlines] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [timetableEvents, setTimetableEvents] = useState([]);
  const [timetableStatus, setTimetableStatus] = useState(null);
  const [garminStatus, setGarminStatus] = useState(null);

  // Loading & notification states
  const [loadingDateData, setLoadingDateData] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isSubmittingJournal, setIsSubmittingJournal] = useState(false);
  const [toast, setToast] = useState(null);

  // CRM Detail modal
  const [selectedPersonId, setSelectedPersonId] = useState(null);

  // Authentication State
  const [isAuthenticated, setIsAuthenticated] = useState(null); // null = checking, true = unlocked, false = locked

  useEffect(() => {
    checkAuthentication();

    const handleUnauthorized = () => {
      clearStoredToken();
      setIsAuthenticated(false);
    };

    window.addEventListener('command_centre_unauthorized', handleUnauthorized);
    return () => window.removeEventListener('command_centre_unauthorized', handleUnauthorized);
  }, []);

  const checkAuthentication = async () => {
    try {
      const status = await fetchAuthStatus();
      if (!status.auth_required) {
        setIsAuthenticated(true);
        return;
      }

      const token = getStoredToken();
      if (!token) {
        setIsAuthenticated(false);
        return;
      }

      const res = await verifyAuthToken(token);
      if (res && res.valid) {
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
      }
    } catch (err) {
      setIsAuthenticated(false);
    }
  };

  const handleUnlock = (token) => {
    setStoredToken(token);
    setIsAuthenticated(true);
  };

  const handleLock = () => {
    clearStoredToken();
    setIsAuthenticated(false);
  };

  // Initial load when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadGarminStatus();
      loadPeople();
      loadUniversityData();
    }
  }, [isAuthenticated]);

  // When selectedDate changes, load metrics and journal
  useEffect(() => {
    if (isAuthenticated) {
      loadDateData(selectedDate);
    }
  }, [selectedDate, isAuthenticated]);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadGarminStatus = async () => {
    try {
      const status = await fetchGarminStatus();
      setGarminStatus(status);
    } catch (err) {
      console.error('Failed to load Garmin status:', err);
    }
  };

  const loadPeople = async () => {
    try {
      const list = await fetchPeople();
      setPeople(list);
    } catch (err) {
      console.error('Failed to load people:', err);
    }
  };

  const loadUniversityData = async () => {
    try {
      const [mods, dls, tks, tt, ttStat] = await Promise.all([
        fetchModules(),
        fetchDeadlines(),
        fetchAcademicTasks(),
        fetchTimetable({ limit: 2500 }),
        fetchTimetableStatus()
      ]);
      setModules(mods);
      setDeadlines(dls);
      setTasks(tks);
      setTimetableEvents(tt);
      setTimetableStatus(ttStat);
    } catch (err) {
      console.error('Failed to load university data:', err);
    }
  };

  const loadDateData = async (dateStr) => {
    setLoadingDateData(true);
    try {
      const [metricData, entriesData] = await Promise.all([
        fetchDailyMetrics(dateStr),
        fetchJournalEntriesForDate(dateStr)
      ]);
      setMetrics(metricData);
      setJournalEntries(entriesData);
    } catch (err) {
      console.error('Error loading daily data:', err);
    } finally {
      setLoadingDateData(false);
    }
  };

  const handleSyncGarmin = async () => {
    setIsSyncing(true);
    try {
      const updatedMetrics = await syncGarmin(selectedDate);
      setMetrics(updatedMetrics);
      showToast(`Garmin telemetry synced for ${selectedDate}`);
      loadGarminStatus();
    } catch (err) {
      showToast(`Garmin sync failed: ${err.message}`, 'error');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSubmitJournal = async (rawText) => {
    setIsSubmittingJournal(true);
    try {
      const newEntry = await submitJournalEntry(selectedDate, rawText);
      setJournalEntries(prev => [newEntry, ...prev]);
      loadPeople();
      showToast('Journal analyzed and saved with AI insights!');
    } catch (err) {
      showToast(`Extraction failed: ${err.message}`, 'error');
    } finally {
      setIsSubmittingJournal(false);
    }
  };

  const handleDeleteJournal = async (id) => {
    try {
      await deleteJournalEntry(id);
      setJournalEntries(prev => prev.filter(e => e.id !== id));
      showToast('Journal entry removed');
    } catch (err) {
      showToast(`Failed to delete: ${err.message}`, 'error');
    }
  };

  const handlePersonClickByName = (name) => {
    if (!name) return;
    const found = people.find(p => p.name.toLowerCase() === name.toLowerCase() || p.slug === name.toLowerCase());
    if (found) {
      setSelectedPersonId(found.id);
    } else {
      setActiveTab('people');
    }
  };

  // Urgent deadlines count (< 7 days or overdue)
  const urgentDeadlineCount = deadlines.filter(d => {
    if (d.status === 'submitted' || d.status === 'graded') return false;
    const due = new Date(d.due_date);
    const now = new Date();
    const diffDays = Math.round((due - now) / (1000 * 60 * 60 * 24));
    return diffDays <= 7;
  }).length;

  if (isAuthenticated === null) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (isAuthenticated === false) {
    return <LockScreen onUnlock={handleUnlock} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex">
      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 animate-bounce">
          <div className={`flex items-center gap-2 px-4 py-3 rounded-2xl shadow-2xl border text-xs font-bold ${
            toast.type === 'error'
              ? 'bg-rose-950 text-rose-200 border-rose-800'
              : 'bg-emerald-950 text-emerald-200 border-emerald-800'
          }`}>
            {toast.type === 'error' ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            <span>{toast.message}</span>
            <button onClick={() => setToast(null)} className="ml-2 opacity-70 hover:opacity-100">
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Modern Collapsible Responsive Sidebar */}
      <Sidebar
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        workspace={workspace}
        setWorkspace={setWorkspace}
        garminStatus={garminStatus}
        onSyncGarmin={handleSyncGarmin}
        isSyncing={isSyncing}
        urgentDeadlineCount={urgentDeadlineCount}
        peopleCount={people.length}
        onLock={handleLock}
      />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Floating App Bar */}
        <header className="h-14 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md px-4 sm:px-6 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-3 text-xs">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-xl bg-slate-800/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700/80 transition"
              aria-label="Open Navigation Menu"
            >
              <Menu className="w-4 h-4 text-emerald-400" />
            </button>
            <div className="flex items-center gap-2">
              <span className="font-extrabold uppercase tracking-wider text-slate-400 hidden sm:inline">
                {workspace === 'uni' ? 'University Workspace' : 'Life & Day-to-Day'}
              </span>
              <span className="text-slate-600 hidden sm:inline">/</span>
              <span className="text-white font-bold capitalize">{activeTab}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Quick Chat Shortcut Trigger */}
            {activeTab !== 'chat' && (
              <button
                onClick={() => setActiveTab('chat')}
                className="flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 text-xs font-bold transition shadow-sm"
              >
                <Bot className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Ask AI Assistant</span>
                <span className="sm:hidden">AI</span>
              </button>
            )}
          </div>
        </header>

        {/* View Routing */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 pb-24 md:pb-6">
          {activeTab === 'daily' && (
            <div className="space-y-6 animate-fade-in">
              <DateNavigator 
                selectedDate={selectedDate} 
                onDateChange={setSelectedDate} 
              />

              <SummaryCards 
                metrics={metrics} 
                journalEntries={journalEntries} 
              />

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 min-h-[560px]">
                <JournalEditor 
                  selectedDate={selectedDate}
                  journalEntries={journalEntries}
                  onSubmitEntry={handleSubmitJournal}
                  onDeleteEntry={handleDeleteJournal}
                  onPersonClick={handlePersonClickByName}
                  isSubmitting={isSubmittingJournal}
                />

                <DailyTimeline 
                  metrics={metrics}
                  journalEntries={journalEntries}
                  onPersonClick={handlePersonClickByName}
                />
              </div>
            </div>
          )}

          {activeTab === 'uni' && (
            <div className="animate-fade-in">
              <UniversityDashboard
                modules={modules}
                deadlines={deadlines}
                tasks={tasks}
                timetableEvents={timetableEvents}
                timetableStatus={timetableStatus}
                onRefreshData={loadUniversityData}
                onShowToast={showToast}
              />
            </div>
          )}

          {activeTab === 'people' && (
            <div className="animate-fade-in">
              <PeopleDirectory 
                people={people} 
                onSelectPerson={(id) => setSelectedPersonId(id)} 
              />
            </div>
          )}

          {activeTab === 'chat' && (
            <div className="animate-fade-in">
              <ChatAssistant />
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="animate-fade-in">
              <SettingsModal 
                garminStatus={garminStatus}
                onRefreshGarminStatus={loadGarminStatus}
                onDataSeeded={() => {
                  loadDateData(selectedDate);
                  loadPeople();
                  loadUniversityData();
                  loadGarminStatus();
                  showToast('7-Day Demo & University data populated!');
                }}
              />
            </div>
          )}
        </main>
      </div>

      {/* Person Detail Slide-Over / Modal */}
      {selectedPersonId && (
        <PersonModal 
          personId={selectedPersonId}
          onClose={() => setSelectedPersonId(null)}
          onUpdated={() => loadPeople()}
          onDeleted={() => {
            setSelectedPersonId(null);
            loadPeople();
          }}
        />
      )}

      {/* Mobile Bottom Navigation Bar */}
      <nav className="md:hidden fixed bottom-0 inset-x-0 bg-slate-900/95 border-t border-slate-800/80 backdrop-blur-xl z-30 px-3 py-1 flex items-center justify-around select-none">
        <button
          onClick={() => { setActiveTab('daily'); setWorkspace('life'); }}
          className={`flex flex-col items-center gap-1 py-1.5 px-3 rounded-xl transition ${
            activeTab === 'daily' ? 'text-emerald-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <LayoutDashboard className="w-4 h-4" />
          <span className="text-[10px]">Life</span>
        </button>

        <button
          onClick={() => { setActiveTab('uni'); setWorkspace('uni'); }}
          className={`flex flex-col items-center gap-1 py-1.5 px-3 rounded-xl transition relative ${
            activeTab === 'uni' ? 'text-indigo-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <GraduationCap className="w-4 h-4" />
          <span className="text-[10px]">Uni</span>
          {urgentDeadlineCount > 0 && (
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400 absolute top-1 right-2" />
          )}
        </button>

        <button
          onClick={() => setActiveTab('people')}
          className={`flex flex-col items-center gap-1 py-1.5 px-3 rounded-xl transition ${
            activeTab === 'people' ? 'text-cyan-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Users className="w-4 h-4" />
          <span className="text-[10px]">People</span>
        </button>

        <button
          onClick={() => setActiveTab('chat')}
          className={`flex flex-col items-center gap-1 py-1.5 px-3 rounded-xl transition ${
            activeTab === 'chat' ? 'text-amber-400 font-bold' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <Bot className="w-4 h-4" />
          <span className="text-[10px]">AI</span>
        </button>

        <button
          onClick={() => setMobileMenuOpen(true)}
          className="flex flex-col items-center gap-1 py-1.5 px-3 rounded-xl transition text-slate-400 hover:text-white"
        >
          <Menu className="w-4 h-4" />
          <span className="text-[10px]">Menu</span>
        </button>
      </nav>
    </div>
  );
}
