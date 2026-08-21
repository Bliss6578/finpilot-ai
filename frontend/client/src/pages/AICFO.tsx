/**
 * Flight Deck design reminder: the AI CFO is a calm financial analyst, mixing concise narrative with structured evidence and a clear recommendation rather than chat-only answers.
 */
import { FormEvent, useState } from "react";
import { Database, Send, Sparkles } from "lucide-react";
import { Panel, SectionLabel } from "@/components/finpilot-ui";
import { suggestedQuestions } from "@/data/mockData";

type Message = { role: "user" | "assistant"; text: string };
export default function AICFO() {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [thinking, setThinking] = useState(false);
  const ask = (question: string) => {
    if (!question.trim() || thinking) return;
    setMessages(current => [...current, { role: "user", text: question }]);
    setDraft("");
    setThinking(true);
    window.setTimeout(() => {
      setMessages(current => [
        ...current,
        {
          role: "assistant",
          text: "Profit decreased approximately 7.2% compared with last month. The decline is concentrated in a few controllable operating signals.",
        },
      ]);
      setThinking(false);
    }, 550);
  };
  const submit = (event: FormEvent) => {
    event.preventDefault();
    ask(draft);
  };
  return (
    <>
      <div className="page-header">
        <div>
          <SectionLabel>Contextual finance intelligence</SectionLabel>
          <h1>Explain the reserve breach</h1>
          <p>
            Ask FinPilot for the drivers, trade-offs, and actions behind your
            most important finance signals.
          </p>
        </div>
      </div>
      <section className="ai-layout">
        <Panel className="chat-surface">
          <div className="chat-message-list">
            {messages.length === 0 && (
              <>
                <div className="ai-welcome">
                  <span className="mini-status">
                    <i />
                    Your current finance context is connected
                  </span>
                  <h2>Ask the question behind the numbers.</h2>
                  <p>
                    FinPilot combines payments, settlement timing, and your
                    financial preferences into a useful operating answer.
                  </p>
                </div>
                <div className="suggested-list">
                  {suggestedQuestions.map(question => (
                    <button
                      className="suggested-question"
                      key={question}
                      onClick={() => ask(question)}
                    >
                      {question}
                    </button>
                  ))}
                </div>
              </>
            )}
            {messages.map((message, index) => (
              <ChatMessage key={`${message.role}-${index}`} {...message} />
            ))}
            {thinking && (
              <div className="message">
                <div className="message-avatar">
                  <Sparkles />
                </div>
                <div className="message-copy">
                  <div className="answer-heading">
                    <i />
                    FinPilot is analysing your finances
                  </div>
                  <span className="id-code">
                    Connecting payment, refund and forecast signals…
                  </span>
                </div>
              </div>
            )}
          </div>
          <form className="ai-input-area" onSubmit={submit}>
            <div className="ai-input">
              <input
                value={draft}
                onChange={event => setDraft(event.target.value)}
                placeholder="Ask FinPilot about your finances…"
              />
              <button aria-label="Send question">
                <Send />
              </button>
            </div>
            <small>
              FinPilot uses your connected financial data to provide contextual
              insights.
            </small>
          </form>
        </Panel>
        <aside className="ai-rail">
          <Panel className="ai-rail-panel">
            <SectionLabel>Data sources</SectionLabel>
            <h3>Analysis is grounded in your business signals.</h3>
            <div className="ai-data-source">
              <div className="source-icon">
                <Database />
              </div>
              <div>
                <strong>Razorpay</strong>
                <span>Payments, settlements, refunds</span>
              </div>
            </div>
            <div className="ai-data-source">
              <div className="source-icon">
                <Sparkles />
              </div>
              <div>
                <strong>FinPilot forecasts</strong>
                <span>Cash-flow and risk modelling</span>
              </div>
            </div>
          </Panel>
          <Panel className="ai-rail-panel">
            <div className="ai-insight-image" aria-hidden="true">
              <Sparkles />
            </div>
            <SectionLabel>Current focus</SectionLabel>
            <h3>Cash buffer integrity</h3>
            <p>
              FinPilot is monitoring the projected Sep 12 reserve breach and the
              refund variance contributing to it.
            </p>
            <div className="ai-health-line">
              <span>Finance health score</span>
              <strong>87 / 100</strong>
            </div>
          </Panel>
        </aside>
      </section>
    </>
  );
}
function ChatMessage({ role, text }: Message) {
  if (role === "user")
    return (
      <div className="message user">
        <div className="message-avatar user-avatar">M</div>
        <div className="message-copy">{text}</div>
      </div>
    );
  return (
    <div className="message">
      <div className="message-avatar">
        <Sparkles />
      </div>
      <div className="message-copy">
        <div className="answer-heading">
          <i />
          FinPilot analysis
        </div>
        {text}
        <div className="answer-metrics">
          <div className="answer-metric">
            <span>Refunds</span>
            <strong>+₹18,400</strong>
          </div>
          <div className="answer-metric">
            <span>Advertising</span>
            <strong>+₹24,000</strong>
          </div>
          <div className="answer-metric">
            <span>Average order value</span>
            <strong>−4.2%</strong>
          </div>
        </div>
        <div className="recommendation">
          <span>FinPilot recommendation</span>
          <p>
            Your largest controllable increase came from marketing spend. Review
            campaigns with low returns before expanding the budget.
          </p>
        </div>
      </div>
    </div>
  );
}
