/** AI CFO answers are rendered only from the authenticated workspace API. */
import { FormEvent, useEffect, useRef, useState } from "react";
import { Check, Database, RefreshCw, Send, Sparkles } from "lucide-react";
import { useLocation } from "wouter";
import { Panel, SectionLabel } from "@/components/finpilot-ui";
import { askAICFO, fetchAICFOContext, type AICFOContext, type AICFOResponse } from "@/services/api";

type Message =
  | { role: "user"; text: string }
  | { role: "assistant"; response: AICFOResponse };

const fallbackQuestions = [
  "What is my net payment revenue this month?",
  "Why are my refunds changing?",
  "How healthy is my payment success rate?",
  "What does my 30-day cash-flow forecast show?",
];

export default function AICFO() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [context, setContext] = useState<AICFOContext | null>(null);
  const [thinking, setThinking] = useState(false);
  const [conversationId, setConversationId] = useState<string>();
  const [, setLocation] = useLocation();
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const loadContext = async () => {
    try {
      setContext(await fetchAICFOContext());
      setError(null);
    } catch {
      setError("FinPilot could not read this workspace's financial context.");
    }
  };

  useEffect(() => { void loadContext(); }, []);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, thinking]);

  const ask = async (question: string) => {
    const cleanQuestion = question.trim();
    if (!cleanQuestion || thinking) return;
    setMessages(current => [...current, { role: "user", text: cleanQuestion }]);
    setDraft("");
    setThinking(true);
    setError(null);
    try {
      const response = await askAICFO(cleanQuestion, conversationId);
      setConversationId(response.conversation_id);
      setMessages(current => [...current, { role: "assistant", response }]);
      await loadContext();
    } catch {
      setError("FinPilot could not complete that analysis. Refresh the financial context and try again.");
    } finally {
      setThinking(false);
    }
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    void ask(draft);
  };
  const lastAnswer = [...messages].reverse().find(
    (message): message is Extract<Message, { role: "assistant" }> => message.role === "assistant",
  );
  const questions = lastAnswer?.response.suggestions ?? context?.suggestions ?? fallbackQuestions;
  const latestData = context?.latest_data_at
    ? new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(context.latest_data_at))
    : "No synchronized activity yet";

  return <>
    <div className="page-header">
      <div>
        <SectionLabel>Contextual finance intelligence</SectionLabel>
        <h1>Ask your financial evidence.</h1>
        <p>Every answer is calculated inside the signed-in workspace from its Razorpay records and FinPilot forecast.</p>
      </div>
      <button className="button-secondary" onClick={() => void loadContext()}><RefreshCw />Refresh context</button>
    </div>
    <section className="ai-layout">
      <Panel className="chat-surface">
        <div className="chat-message-list">
          {messages.length === 0 && <div className="ai-welcome">
            <span className="mini-status"><i />{context ? `${context.payment_attempts} payment attempts available in this 30-day context` : "Connecting this workspace's finance context"}</span>
            <h2>Ask the question behind the numbers.</h2>
            <p>FinPilot distinguishes measured evidence from modeled assumptions and says when a data source is missing.</p>
          </div>}
          {messages.map((message, index) => <ChatMessage key={`${message.role}-${index}`} message={message} onAction={setLocation} />)}
          {thinking && <div className="message">
            <div className="message-avatar"><Sparkles /></div>
            <div className="message-copy"><div className="answer-heading"><i />FinPilot is analysing this workspace</div><span className="id-code">Comparing payments, refunds, settlements and forecast evidence…</span></div>
          </div>}
          {!thinking && <div className="suggested-list follow-up-queries">
            {questions.map(question => <button className="suggested-question" key={question} onClick={() => void ask(question)}>{question}</button>)}
          </div>}
          {error && <div className="api-error"><strong>Analysis unavailable</strong><span>{error}</span></div>}
          <div ref={endRef} />
        </div>
        <form className="ai-input-area" onSubmit={submit}>
          <div className="ai-input"><input value={draft} onChange={event => setDraft(event.target.value)} placeholder="Ask FinPilot about your finances…" maxLength={600} /><button aria-label="Send question" disabled={thinking || !draft.trim()}><Send /></button></div>
          <small>Answers use only this workspace. Payment proceeds are not described as accounting profit without expense data.</small>
        </form>
      </Panel>
      <aside className="ai-rail">
        <Panel className="ai-rail-panel">
          <SectionLabel>Verified data sources</SectionLabel><h3>Analysis is grounded in this business.</h3>
          <div className="ai-data-source"><div className="source-icon"><Database /></div><div><strong>Razorpay · {context?.mode ?? "test"} mode</strong><span>Payments, settlements and refunds</span></div></div>
          <div className="ai-data-source"><div className="source-icon"><Sparkles /></div><div><strong>FinPilot forecast</strong><span>{context?.focus.cashflow_source.replaceAll("_", " ") ?? "Loading model source"}</span></div></div>
        </Panel>
        <Panel className="ai-rail-panel">
          <div className="ai-insight-image" aria-hidden="true"><Sparkles /></div><SectionLabel>Current focus</SectionLabel>
          <h3>{context?.focus.title ?? "Reading business context"}</h3><p>{context?.focus.description ?? "FinPilot is calculating the current evidence-backed focus."}</p>
          <div className="ai-health-line"><span>Latest financial record</span><strong>{latestData}</strong></div>
        </Panel>
      </aside>
    </section>
  </>;
}

function ChatMessage({ message, onAction }: { message: Message; onAction: (path: string) => void }) {
  if (message.role === "user") return <div className="message user"><div className="message-avatar user-avatar">Y</div><div className="message-copy">{message.text}</div></div>;
  const { response } = message;
  return <div className="message">
    <div className="message-avatar"><Sparkles /></div>
    <div className="message-copy">
      <div className="answer-heading"><i />FinPilot analysis · {response.evidence.mode} mode</div>
      <p>{response.answer}</p>
      {!!response.tools_used?.length && <div className="id-code">{response.tools_used.map(tool => <span key={tool} style={{ marginRight: 14 }}><Check size={12} /> {tool.replaceAll("_", " ")}</span>)}</div>}
      <div className="answer-metrics">{response.metrics.map(metric => <div className="answer-metric" key={metric.label}><span>{metric.label}</span><strong>{metric.value}</strong><small>{metric.detail}</small></div>)}</div>
      <div className="recommendation"><span>Evidence-backed recommendation</span><p>{response.recommendation}</p></div>
      {!!response.actions?.length && <div className="suggested-list">{response.actions.map(action => <button className="button-secondary" key={action.action} onClick={() => onAction(action.action.includes("scenario") ? "/scenario-lab" : action.action.includes("cash") ? "/cash-flow" : "/transactions")}>{action.label}</button>)}</div>}
      <div className="id-code">Sources · {response.evidence.sources.join(" · ")}</div>
    </div>
  </div>;
}
