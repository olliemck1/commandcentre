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
import { CheckCircle2, AlertTriangle, X, Menu, Search, Bot } from 'lucide-react';

export default function App() {
  const [selectedDate, setSelectedDate] = useState(getTodayString());
  
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

      {/* Modern Collapsible Sidebar */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        workspace={workspace}
        setWorkspace={setWorkspace}
        garminStatus={garminStatus}
        onSyncGarmin={handleSyncGarmin}
        isSyncing={isSyncing}
        urgentDeadlineCount={urgentDeadlineCount}
        peopleCount={people.length}
      />

      {/* Main Content Workspace */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Floating App Bar */}
        <header className="h-14 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-30">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-extrabold uppercase tracking-wider text-slate-400">
              {workspace === 'uni' ? 'University Workspace' : 'Life & Day-to-Day'}
            </span>
            <span className="text-slate-600">/</span>
            <span className="text-white font-bold capitalize">{activeTab}</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Quick Chat Shortcut Trigger */}
            {activeTab !== 'chat' && (
              <button
                onClick={() => setActiveTab('chat')}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/20 text-xs font-bold transition shadow-sm"
              >
                <Bot className="w-3.5 h-3.5" />
                <span>Ask AI Assistant</span>
              </button>
            )}
          </div>
        </header>

        {/* View Routing */}
        <main className="flex-1 max-w-7xl w-full mx-auto p-6">
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
    </div>
  );
}
