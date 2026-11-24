
import { useState } from "react";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  async function sendMessage(e) {
    e.preventDefault();

    const message = input.trim();
    if (!message || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Something went wrong.");
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          metadata: data.metadata,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: error.message },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app">
      <header className="header">
        <div className="brand">
          <div className="brand-icon">✦</div>
          <div>
            <h1>Lyftr AI</h1>
            <p>Your intelligent AI assistant</p>
          </div>
        </div>
        <span className="status"><span /> AI Online</span>
      </header>

      <section className="chat">
        <div className="welcome">
          <div className="welcome-icon">✦</div>
          <h2>How can I help you today?</h2>
          <p>Ask anything. Your conversation is powered by Lyftr AI.</p>
        </div>

        <div className="messages">
          {messages.map((msg, index) => (
            <div
              className={`message ${msg.role}`}
              key={index}
              data-testid={msg.role === "assistant" ? "assistant-message" : undefined}
            >
              <div className="message-label">
                {msg.role === "user" ? "You" : msg.role === "assistant" ? "Lyftr AI" : "Error"}
              </div>
              <div className="message-content">{msg.content}</div>

              {msg.metadata && (
                <div className="metadata">
                  <span data-testid="meta-source">
                    {msg.metadata.resolution_source}
                  </span>
                  <span data-testid="meta-model">{msg.metadata.model}</span>
                  <span data-testid="meta-latency">
                    {msg.metadata.latency_ms} ms
                  </span>
                  <span data-testid="meta-input-tokens">
                    Input: {msg.metadata.input_tokens}
                  </span>
                  <span data-testid="meta-output-tokens">
                    Output: {msg.metadata.output_tokens}
                  </span>
                </div>
              )}
            </div>
          ))}
          {loading && <div className="loading">Lyftr AI is thinking...</div>}
        </div>
      </section>

      <form className="composer" onSubmit={sendMessage}>
        <textarea
          data-testid="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message Lyftr AI..."
          rows="1"
          disabled={loading}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.form.requestSubmit();
            }
          }}
        />
        <button
          data-testid="send-button"
          type="submit"
          disabled={loading || !input.trim()}
        >
          {loading ? "..." : "Send ↑"}
        </button>
      </form>

      <footer>Powered by Lyftr AI · Responses may occasionally be inaccurate</footer>
    </main>
  );
}

export default App;
