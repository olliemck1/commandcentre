import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  Sparkles, 
  Trash2, 
  Calendar, 
  Clock, 
  ExternalLink, 
  ChevronDown, 
  ChevronUp,
  Activity,
  GraduationCap,
  Users,
  Utensils,
  BookOpen
} from 'lucide-react';
import { streamChatMessage } from '../api/client';

const SUGGESTED_PROMPTS = [
  "What assignments are due this week and how many calories did I eat yesterday?",
  "What did I do yesterday and what did I talk about with Sam?",
  "When was the last time I saw Alex and what was his new job?",
  "Summarize my steps and sleep for today."
];

export default function ChatAssistant() {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I am your **Command Centre AI Assistant**. I have real-time query access to your **Garmin physical telemetry**, **dietary nutrition logs**, **daily journal entries**, **people network CRM**, and **University coursework deadlines & tasks**.\n\nHow can I help you today?",
      citations: []
    }
  ]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [expandedCitations, setExpandedCitations] = useState({});

  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isStreaming]);

  const toggleCitationExpand = (msgId) => {
    setExpandedCitations(prev => ({
      ...prev,
      [msgId]: !prev[msgId]
    }));
  };

  const handleSend = async (textToSend = null) => {
    const query = (textToSend || input).trim();
    if (!query || isStreaming) return;

    setInput('');

    // Add user message
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query
    };

    // Prepare assistant message
    const assistantMsgId = `asst-${Date.now()}`;
    const assistantMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      citations: [],
      tools: []
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setIsStreaming(true);

    const history = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));

    await streamChatMessage(query, history, {
      onTools: (tools) => {
        setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, tools } : m));
      },
      onDelta: (deltaText) => {
        setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content: m.content + deltaText } : m));
      },
      onCitations: (citations) => {
        setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, citations } : m));
      },
      onDone: () => {
        setIsStreaming(false);
      },
      onError: (err) => {
        console.error('Chat stream error:', err);
        setMessages(prev => prev.map(m => m.id === assistantMsgId ? { ...m, content: m.content + `\n\n*(Error: ${err.message})*` } : m));
        setIsStreaming(false);
      }
    });
  };

  const handleClear = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: "Chat history cleared. How can I assist you with your life or academic tasks?",
        citations: []
      }
    ]);
  };

  const renderCitationIcon = (type) => {
    switch (type) {
      case 'deadline':
        return <GraduationCap className="w-3.5 h-3.5 text-indigo-400" />;
      case 'garmin':
        return <Activity className="w-3.5 h-3.5 text-emerald-400" />;
      case 'person':
      case 'interaction':
        return <Users className="w-3.5 h-3.5 text-cyan-400" />;
      case 'nutrition':
        return <Utensils className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <BookOpen className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl flex flex-col h-[calc(100vh-6rem)] overflow-hidden">
      {/* Chat Top Header */}
      <div className="px-6 py-4 border-b border-slate-800/80 bg-slate-950/60 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-amber-500 to-orange-400 p-[1.5px] shadow-md shadow-amber-950/40">
            <div className="w-full h-full bg-slate-950 rounded-[10px] flex items-center justify-center">
              <Bot className="w-4 h-4 text-amber-400" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-extrabold text-white tracking-tight">AI Intelligence Assistant</h2>
              <span className="text-[10px] font-mono font-bold px-1.5 py-0.2 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Multi-Domain Tools Active
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Contextual query access across Garmin, Nutrition, Journal, CRM, and University</p>
          </div>
        </div>

        <button
          onClick={handleClear}
          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-slate-800 transition"
          title="Clear Conversation"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>

      {/* Message Stream */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.map((msg) => {
          const isUser = msg.role === 'user';
          const hasCitations = msg.citations && msg.citations.length > 0;
          const isExpanded = expandedCitations[msg.id] ?? false;

          return (
            <div key={msg.id} className={`flex gap-3.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
              {!isUser && (
                <div className="w-8 h-8 rounded-xl bg-slate-950 border border-slate-800 text-amber-400 flex items-center justify-center shrink-0 mt-1 shadow">
                  <Bot className="w-4 h-4" />
                </div>
              )}

              <div className={`max-w-2xl space-y-3 ${isUser ? 'items-end' : 'items-start'}`}>
                {/* Speech Bubble */}
                <div className={`rounded-2xl p-4 text-xs leading-relaxed ${
                  isUser 
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-950/40 rounded-tr-sm' 
                    : 'bg-slate-950/90 border border-slate-800/80 text-slate-200 shadow-md rounded-tl-sm'
                }`}>
                  <div className="whitespace-pre-line prose prose-invert prose-xs max-w-none">
                    {msg.content || (isStreaming ? 'Thinking and retrieving records...' : '')}
                  </div>
                </div>

                {/* Source Citations Pill Container */}
                {hasCitations && (
                  <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 space-y-2 text-xs">
                    <button
                      onClick={() => toggleCitationExpand(msg.id)}
                      className="w-full flex items-center justify-between text-[11px] font-bold text-slate-400 hover:text-slate-200 transition"
                    >
                      <div className="flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                        <span>Sources & Evidence ({msg.citations.length} records cited)</span>
                      </div>
                      {isExpanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                    </button>

                    {isExpanded && (
                      <div className="grid grid-cols-1 gap-2 pt-2 border-t border-slate-800/80">
                        {msg.citations.map((cite, cIdx) => (
                          <div 
                            key={cIdx} 
                            className="bg-slate-900 p-2 rounded-lg border border-slate-800 flex items-start gap-2.5 text-[11px]"
                          >
                            <div className="p-1 rounded bg-slate-950 border border-slate-800 shrink-0 mt-0.5">
                              {renderCitationIcon(cite.type)}
                            </div>
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center justify-between">
                                <span className="font-bold text-white truncate">{cite.title}</span>
                                {cite.date && <span className="text-[10px] font-mono text-slate-500">{cite.date}</span>}
                              </div>
                              <p className="text-slate-400 line-clamp-2 mt-0.5 text-[10px]">
                                {cite.snippet}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompt Chips */}
      <div className="px-6 py-2 bg-slate-950/80 border-t border-slate-800/60 flex items-center gap-2 overflow-x-auto">
        <span className="text-[11px] text-slate-500 font-bold shrink-0">Try:</span>
        {SUGGESTED_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(prompt)}
            disabled={isStreaming}
            className="text-[11px] px-3 py-1 rounded-lg bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 hover:text-white transition whitespace-nowrap shrink-0"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Bar */}
      <div className="p-4 bg-slate-950 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex items-center gap-3"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            placeholder="Ask anything about your life, Garmin stats, meals, contacts, or uni deadlines..."
            className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500/80 transition"
          />

          <button
            type="submit"
            disabled={!input.trim() || isStreaming}
            className={`px-5 py-2.5 rounded-xl text-xs font-bold transition flex items-center gap-2 ${
              !input.trim() || isStreaming
                ? 'bg-slate-800 text-slate-500 border border-slate-700/40 cursor-not-allowed'
                : 'bg-amber-600 hover:bg-amber-500 text-white shadow-lg shadow-amber-950/60 active:scale-95'
            }`}
          >
            <Send className={`w-3.5 h-3.5 ${isStreaming ? 'animate-pulse' : ''}`} />
            <span>{isStreaming ? 'Streaming...' : 'Ask'}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
