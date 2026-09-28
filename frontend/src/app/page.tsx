"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";

/* ─── Types ──────────────────────────────────────────────────────── */
interface WorkflowEvent {
  event: string;
  timestamp: string;
  details?: Record<string, unknown>;
}
interface ToolResult {
  tool_name: string;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  status: string;
}
interface PendingAction {
  action_id: string;
  session_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  description: string;
  status: string;
}
interface PlanStep {
  step: number;
  title: string;
  details: string;
}
interface Plan {
  goal: string;
  summary: string;
  steps: PlanStep[];
  recommended_place: Record<string, string>;
  weather_info: Record<string, string>;
}
interface ChatResponse {
  session_id: string;
  message: string;
  workflow_events: WorkflowEvent[];
  tool_results: ToolResult[];
  pending_action: PendingAction | null;
  plan: Plan | null;
  final_result: string | null;
  context_used?: string | null;
  retry_info?: string | null;
}
interface Message {
  id: string;
  sender: "user" | "assistant";
  content: string;
  timestamp: string;
  toolResults?: ToolResult[];
  plan?: Plan | null;
  pendingAction?: PendingAction | null;
  workflowEvents?: WorkflowEvent[];
  contextUsed?: string | null;
  retryInfo?: string | null;
}

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* ─── Helpers ────────────────────────────────────────────────────── */
function genId() {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
}

/* ─── Icons (inline SVG) ─────────────────────────────────────────── */
const MicIcon = ({ active }: { active: boolean }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke={active ? "#ef4444" : "currentColor"} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
    <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
    <line x1="12" y1="19" x2="12" y2="23" />
    <line x1="8" y1="23" x2="16" y2="23" />
  </svg>
);
const SendIcon = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="22" y1="2" x2="11" y2="13" />
    <polygon points="22 2 15 22 11 13 2 9 22 2" />
  </svg>
);
const WeatherIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
  </svg>
);
const PlaceIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" />
    <circle cx="12" cy="10" r="3" />
  </svg>
);
const PlanIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8b5cf6" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" />
  </svg>
);
const ReminderIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#06d6f2" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
  </svg>
);
const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

/* ─── Component ─────────────────────────────────────────────────── */
export default function ActionFlowApp() {
  const [sessionId] = useState(() => "session_" + genId());
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [currentEvents, setCurrentEvents] = useState<WorkflowEvent[]>([]);
  const [showHero, setShowHero] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const [actionConfirmed, setActionConfirmed] = useState<Record<string, "confirmed" | "cancelled">>({});

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const recognitionRef = useRef<any>(null);

  // Auto-scroll
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, currentEvents]);

  // Focus input
  useEffect(() => { inputRef.current?.focus(); }, [showHero]);

  /* ─── Voice ──────────────────────────────────────────────── */
  const toggleVoice = useCallback(() => {
    if (typeof window === "undefined") return;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const win = window as any;
    const SpeechRecognitionClass = win.SpeechRecognition || win.webkitSpeechRecognition;
    if (!SpeechRecognitionClass) return;

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }
    const recognition = new SpeechRecognitionClass();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (e: any) => {
      const transcript = e.results[0][0].transcript;
      setInput(prev => prev + (prev ? " " : "") + transcript);
    };
    recognition.onend = () => setIsListening(false);
    recognition.onerror = () => setIsListening(false);
    recognitionRef.current = recognition;
    recognition.start();
    setIsListening(true);
  }, [isListening]);

  /* ─── Send Message ─────────────────────────────────────── */
  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setShowHero(false);
    setInput("");
    setCurrentEvents([]);

    const userMsg: Message = { id: genId(), sender: "user", content: text, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });
      if (!res.ok) throw new Error(`Server error ${res.status}`);
      const data: ChatResponse = await res.json();

      // Animate workflow events
      for (let i = 0; i < data.workflow_events.length; i++) {
        await new Promise(r => setTimeout(r, 350));
        setCurrentEvents(prev => [...prev, data.workflow_events[i]]);
      }
      await new Promise(r => setTimeout(r, 300));

      const assistantMsg: Message = {
        id: genId(),
        sender: "assistant",
        content: data.message,
        timestamp: new Date().toISOString(),
        toolResults: data.tool_results,
        plan: data.plan,
        pendingAction: data.pending_action,
        workflowEvents: data.workflow_events,
        contextUsed: data.context_used,
        retryInfo: data.retry_info,
      };
      setMessages(prev => [...prev, assistantMsg]);
      setCurrentEvents([]);
    } catch (err) {
      const errMsg: Message = {
        id: genId(), sender: "assistant",
        content: `Something went wrong. Please make sure the backend is running at ${API}. Error: ${err instanceof Error ? err.message : "Unknown"}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errMsg]);
    }
    setLoading(false);
  };

  /* ─── Confirm / Cancel ─────────────────────────────────── */
  const handleConfirm = async (actionId: string) => {
    if (actionConfirmed[actionId]) return;
    try {
      const res = await fetch(`${API}/api/actions/${actionId}/confirm`, { method: "POST" });
      if (!res.ok) throw new Error("Confirmation failed");
      const data = await res.json();
      setActionConfirmed(prev => ({ ...prev, [actionId]: "confirmed" }));
      const msg: Message = { id: genId(), sender: "assistant", content: data.message, timestamp: new Date().toISOString() };
      setMessages(prev => [...prev, msg]);
    } catch {
      setActionConfirmed(prev => ({ ...prev, [actionId]: "confirmed" }));
    }
  };
  const handleCancel = async (actionId: string) => {
    if (actionConfirmed[actionId]) return;
    try {
      const res = await fetch(`${API}/api/actions/${actionId}/cancel`, { method: "POST" });
      if (!res.ok) throw new Error("Cancel failed");
      const data = await res.json();
      setActionConfirmed(prev => ({ ...prev, [actionId]: "cancelled" }));
      const msg: Message = { id: genId(), sender: "assistant", content: data.message, timestamp: new Date().toISOString() };
      setMessages(prev => [...prev, msg]);
    } catch {
      setActionConfirmed(prev => ({ ...prev, [actionId]: "cancelled" }));
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  /* ─── Render ───────────────────────────────────────────── */
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--gradient-hero)" }}>
      {/* ── Header ─────────────────────────────────────────── */}
      <header className="flex items-center justify-between px-6 py-3 border-b" style={{ borderColor: "var(--border-color)", background: "rgba(10,14,26,0.85)", backdropFilter: "blur(12px)" }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: "var(--gradient-accent)" }}>
            <span className="text-white font-bold text-sm">AF</span>
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight" style={{ color: "var(--text-primary)" }}>ActionFlow</h1>
            <p className="text-[10px] tracking-[0.25em] uppercase" style={{ color: "var(--text-muted)" }}>Plan • Orchestrate • Act</p>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
          <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          MCP Active
        </div>
      </header>

      {/* ── Main Area ───────────────────────────────────────── */}
      <main className="flex-1 flex flex-col max-w-4xl mx-auto w-full">
        {showHero ? (
          /* ── Hero ─────────────────────────────────────────── */
          <div className="flex-1 flex flex-col items-center justify-center px-6 py-16" style={{ animation: "fadeIn 0.6s ease" }}>
            <div className="w-20 h-20 rounded-2xl flex items-center justify-center mb-8" style={{ background: "var(--gradient-accent)", animation: "orb-float 3s ease-in-out infinite", boxShadow: "var(--glow-cyan)" }}>
              <span className="text-white text-3xl font-extrabold">AF</span>
            </div>
            <h2 className="text-4xl font-extrabold mb-3 text-center" style={{ background: "var(--gradient-accent)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              What would you like to accomplish?
            </h2>
            <p className="text-center mb-10 max-w-xl" style={{ color: "var(--text-secondary)" }}>
              ActionFlow is your agentic assistant. Describe your goal and watch it plan, orchestrate tools, and act — step by step.
            </p>
            <div className="grid gap-3 w-full max-w-lg">
              {[
                "Plan my evening after college. Check the weather, find a nearby activity, and remind me at 6 PM.",
                "What's the weather like today in New York?",
                "Find coffee shops near campus.",
              ].map((s, i) => (
                <button key={i} onClick={() => { setInput(s); setShowHero(false); setTimeout(() => inputRef.current?.focus(), 100); }}
                  className="text-left px-5 py-3.5 rounded-xl border transition-all duration-200 hover:scale-[1.02] cursor-pointer"
                  style={{ background: "var(--bg-card)", borderColor: "var(--border-color)", color: "var(--text-secondary)" }}>
                  <span className="text-sm">{s}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ── Chat ──────────────────────────────────────────── */
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`} style={{ animation: "fadeInUp 0.35s ease" }}>
                <div className={`max-w-[85%] ${msg.sender === "user" ? "" : "w-full max-w-2xl"}`}>
                  {/* Bubble */}
                  <div className="rounded-2xl px-5 py-3.5" style={{
                    background: msg.sender === "user" ? "linear-gradient(135deg, #3b82f6, #2563eb)" : "var(--bg-card)",
                    border: msg.sender === "user" ? "none" : "1px solid var(--border-color)",
                    color: "var(--text-primary)"
                  }}>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  </div>

                  {/* Context and Retry Indicators */}
                  {msg.sender === "assistant" && (msg.contextUsed || msg.retryInfo) && (
                    <div className="mt-2 flex flex-wrap gap-2 text-xs">
                      {msg.contextUsed && (
                        <span className="px-2.5 py-1 rounded-lg border font-medium flex items-center gap-1.5" style={{ background: "rgba(139,92,246,0.12)", borderColor: "rgba(139,92,246,0.3)", color: "var(--accent-purple)" }}>
                          <span>🧠</span> {msg.contextUsed}
                        </span>
                      )}
                      {msg.retryInfo && (
                        <span className="px-2.5 py-1 rounded-lg border font-medium flex items-center gap-1.5" style={{ background: "rgba(245,158,11,0.12)", borderColor: "rgba(245,158,11,0.3)", color: "var(--accent-amber)" }}>
                          <span>⚡</span> {msg.retryInfo}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Tool Cards */}
                  {msg.sender === "assistant" && msg.toolResults && msg.toolResults.length > 0 && (
                    <div className="mt-3 space-y-2.5">
                      {msg.toolResults.map((tr, i) => (
                        <ToolCard key={i} result={tr} />
                      ))}
                    </div>
                  )}

                  {/* Plan Card */}
                  {msg.sender === "assistant" && msg.plan && (
                    <div className="mt-3" style={{ animation: "slideInRight 0.4s ease" }}>
                      <PlanCard plan={msg.plan} />
                    </div>
                  )}

                  {/* Confirmation Card */}
                  {msg.sender === "assistant" && msg.pendingAction && (
                    <div className="mt-3" style={{ animation: "slideInRight 0.4s ease" }}>
                      <ConfirmationCard
                        action={msg.pendingAction}
                        status={actionConfirmed[msg.pendingAction.action_id]}
                        onConfirm={handleConfirm}
                        onCancel={handleCancel}
                      />
                    </div>
                  )}
                </div>
              </div>
            ))}

            {/* Live Workflow Events */}
            {currentEvents.length > 0 && (
              <div className="flex justify-start" style={{ animation: "fadeIn 0.3s ease" }}>
                <div className="max-w-2xl w-full">
                  <WorkflowProgress events={currentEvents} />
                </div>
              </div>
            )}

            {/* Typing indicator */}
            {loading && currentEvents.length === 0 && (
              <div className="flex justify-start">
                <div className="px-5 py-3 rounded-2xl" style={{ background: "var(--bg-card)", border: "1px solid var(--border-color)" }}>
                  <div className="flex gap-1.5">
                    {[0, 1, 2].map(i => (
                      <div key={i} className="w-2 h-2 rounded-full" style={{ background: "var(--accent-cyan)", animation: `typing-dot 1.4s infinite ${i * 0.2}s` }} />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Input Bar ─────────────────────────────────────── */}
        <div className="px-4 pb-5 pt-2">
          <div className="flex items-end gap-2 rounded-2xl p-2 border" style={{ background: "var(--bg-card)", borderColor: "var(--border-color)" }}>
            <button onClick={toggleVoice} title="Voice input" className="p-2.5 rounded-xl transition-all hover:scale-105 cursor-pointer" style={{ background: isListening ? "rgba(239,68,68,0.15)" : "transparent", color: "var(--text-secondary)" }}>
              <MicIcon active={isListening} />
            </button>
            <textarea ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown}
              placeholder="Describe your goal…" rows={1}
              className="flex-1 bg-transparent resize-none text-sm py-2.5 px-1 outline-none placeholder:text-gray-500"
              style={{ color: "var(--text-primary)", minHeight: "40px", maxHeight: "120px" }} />
            <button onClick={sendMessage} disabled={loading || !input.trim()}
              className="p-2.5 rounded-xl transition-all hover:scale-105 disabled:opacity-30 cursor-pointer"
              style={{ background: input.trim() ? "var(--gradient-accent)" : "transparent", color: input.trim() ? "white" : "var(--text-muted)" }}>
              <SendIcon />
            </button>
          </div>
          <p className="text-center text-[11px] mt-2" style={{ color: "var(--text-muted)" }}>
            ActionFlow — Alexa+ style simulated experience backed by a self-hosted MCP server
          </p>
        </div>
      </main>
    </div>
  );
}

/* ─── Sub-Components ────────────────────────────────────────────── */

function WorkflowProgress({ events }: { events: WorkflowEvent[] }) {
  return (
    <div className="rounded-xl p-4 border space-y-2" style={{ background: "rgba(17,24,39,0.7)", borderColor: "var(--border-color)" }}>
      <p className="text-xs font-semibold tracking-wide uppercase mb-2" style={{ color: "var(--accent-cyan)" }}>Workflow Progress</p>
      {events.map((e, i) => (
        <div key={i} className="flex items-center gap-2.5" style={{ animation: "fadeInUp 0.3s ease" }}>
          {i === events.length - 1 ? (
            <div className="w-4 h-4 rounded-full border-2 border-t-transparent animate-spin" style={{ borderColor: "var(--accent-cyan)", borderTopColor: "transparent" }} />
          ) : (
            <CheckIcon />
          )}
          <span className="text-sm" style={{ color: i === events.length - 1 ? "var(--text-primary)" : "var(--text-secondary)" }}>{e.event}</span>
        </div>
      ))}
    </div>
  );
}

function ToolCard({ result }: { result: ToolResult }) {
  const { tool_name, outputs } = result;

  if (tool_name === "get_weather") {
    const w = outputs as Record<string, string>;
    return (
      <div className="rounded-xl p-4 border" style={{ background: "var(--gradient-card)", borderColor: "rgba(245,158,11,0.2)" }}>
        <div className="flex items-center gap-2 mb-3">
          <WeatherIcon />
          <span className="text-sm font-semibold" style={{ color: "var(--accent-amber)" }}>Weather</span>
          <span className="text-xs ml-auto px-2 py-0.5 rounded-full" style={{ background: "rgba(245,158,11,0.12)", color: "var(--accent-amber)" }}>{w.date || "Today"}</span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div><p className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Location</p><p className="text-sm font-medium">{w.location}</p></div>
          <div><p className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Temperature</p><p className="text-sm font-medium">{w.temperature}</p></div>
          <div><p className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Condition</p><p className="text-sm font-medium">{w.weather_condition}</p></div>
          <div><p className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-muted)" }}>Rain Chance</p><p className="text-sm font-medium">{w.precipitation_probability}</p></div>
        </div>
        <p className="mt-3 text-xs px-3 py-2 rounded-lg" style={{ background: "rgba(245,158,11,0.08)", color: "var(--text-secondary)" }}>💡 {w.recommendation}</p>
      </div>
    );
  }

  if (tool_name === "search_places") {
    const places = ((outputs as Record<string, unknown>).places || outputs) as Array<Record<string, string>>;
    return (
      <div className="rounded-xl p-4 border" style={{ background: "var(--gradient-card)", borderColor: "rgba(16,185,129,0.2)" }}>
        <div className="flex items-center gap-2 mb-3">
          <PlaceIcon />
          <span className="text-sm font-semibold" style={{ color: "var(--accent-green)" }}>Nearby Places</span>
        </div>
        <div className="space-y-2">
          {(Array.isArray(places) ? places : []).map((p, i) => (
            <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg" style={{ background: "rgba(16,185,129,0.06)" }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold mt-0.5" style={{ background: "rgba(16,185,129,0.15)", color: "var(--accent-green)" }}>{i + 1}</div>
              <div>
                <p className="text-sm font-medium">{p.name}</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{p.category} · {p.address}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (tool_name === "generate_plan") return null; // Shown as PlanCard
  if (tool_name === "create_reminder" && result.status === "pending_confirmation") return null; // Shown as ConfirmationCard

  // Generic tool card
  return (
    <div className="rounded-xl p-4 border" style={{ background: "var(--gradient-card)", borderColor: "var(--border-color)" }}>
      <p className="text-xs font-semibold mb-2" style={{ color: "var(--accent-blue)" }}>🔧 {tool_name}</p>
      <pre className="text-xs overflow-x-auto" style={{ color: "var(--text-secondary)" }}>{JSON.stringify(outputs, null, 2)}</pre>
    </div>
  );
}

function PlanCard({ plan }: { plan: Plan }) {
  return (
    <div className="rounded-xl p-5 border" style={{ background: "var(--gradient-card)", borderColor: "rgba(139,92,246,0.2)" }}>
      <div className="flex items-center gap-2 mb-3">
        <PlanIcon />
        <span className="text-sm font-semibold" style={{ color: "var(--accent-purple)" }}>Your Plan</span>
      </div>
      <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>{plan.summary}</p>
      <div className="space-y-3">
        {plan.steps.map((s) => (
          <div key={s.step} className="flex gap-3">
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0" style={{ background: "rgba(139,92,246,0.15)", color: "var(--accent-purple)" }}>{s.step}</div>
            <div>
              <p className="text-sm font-medium">{s.title}</p>
              <p className="text-xs" style={{ color: "var(--text-muted)" }}>{s.details}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ConfirmationCard({ action, status, onConfirm, onCancel }: {
  action: PendingAction;
  status?: "confirmed" | "cancelled";
  onConfirm: (id: string) => void;
  onCancel: (id: string) => void;
}) {
  if (status === "confirmed") {
    return (
      <div className="rounded-xl p-4 border flex items-center gap-3" style={{ background: "rgba(16,185,129,0.08)", borderColor: "rgba(16,185,129,0.3)" }}>
        <div className="w-8 h-8 rounded-full flex items-center justify-center" style={{ background: "rgba(16,185,129,0.2)" }}>
          <CheckIcon />
        </div>
        <div>
          <p className="text-sm font-semibold" style={{ color: "var(--accent-green)" }}>Confirmed!</p>
          <p className="text-xs" style={{ color: "var(--text-secondary)" }}>{action.description}</p>
        </div>
      </div>
    );
  }
  if (status === "cancelled") {
    return (
      <div className="rounded-xl p-4 border flex items-center gap-3" style={{ background: "rgba(239,68,68,0.08)", borderColor: "rgba(239,68,68,0.3)" }}>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>Action cancelled.</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl p-4 border" style={{ background: "var(--gradient-card)", borderColor: "rgba(6,214,242,0.25)", animation: "pulse-glow 2s infinite" }}>
      <div className="flex items-center gap-2 mb-3">
        <ReminderIcon />
        <span className="text-sm font-semibold" style={{ color: "var(--accent-cyan)" }}>Confirmation Required</span>
      </div>
      <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>{action.description}</p>
      <div className="flex gap-3">
        <button onClick={() => onConfirm(action.action_id)}
          className="px-5 py-2 rounded-lg text-sm font-semibold transition-all hover:scale-105 cursor-pointer"
          style={{ background: "var(--gradient-accent)", color: "white" }}>
          ✓ Confirm
        </button>
        <button onClick={() => onCancel(action.action_id)}
          className="px-5 py-2 rounded-lg text-sm font-semibold transition-all hover:scale-105 border cursor-pointer"
          style={{ background: "transparent", borderColor: "var(--border-color)", color: "var(--text-secondary)" }}>
          ✕ Cancel
        </button>
      </div>
    </div>
  );
}
