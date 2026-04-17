import { useState } from "react";
import { queryProjectsViaMCP } from "./api/mcpClient";

function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [answer, setAnswer] = useState("");
  const [answerDetails, setAnswerDetails] = useState([]);
  const [answerIntent, setAnswerIntent] = useState("");
  const [answerPrimary, setAnswerPrimary] = useState(null);
  const [prompt, setPrompt] = useState("List out the projects");

  const handleAsk = async (inputPrompt = prompt) => {
    setLoading(true);
    setError("");
    setAnswer("");
    setAnswerDetails([]);
    setAnswerIntent("");
    setAnswerPrimary(null);
    try {
      const result = await queryProjectsViaMCP(inputPrompt);
      setAnswer(result?.answer ?? "");
      setAnswerDetails(result?.details ?? []);
      setAnswerIntent(result?.intent ?? "");
      setAnswerPrimary(result?.primary ?? null);
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to fetch projects.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="header">
        <h1>MyWorkspace Dashboard</h1>
        <p>Microservices orchestrated via MCP Server</p>
      </header>

      <section className="actions">
        <label htmlFor="project-prompt" className="prompt-label">
          Ask project status with a prompt
        </label>
        <textarea
          id="project-prompt"
          rows={3}
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder='Try: What are the channels available OR What are the messages on this "general"'
        />
        <button onClick={() => handleAsk(prompt)} disabled={loading}>
          {loading ? "Processing..." : "Submit"}
        </button>
      </section>

      {error && <p className="error">{error}</p>}
      {(answer || answerDetails.length > 0) && (
        <section className="response-card">
          {answerIntent === "status" && answerPrimary ? (
            <p className="answer">
              The status of <strong>{answerPrimary.name}</strong> is <strong>{answerPrimary.status}</strong>.
            </p>
          ) : (
            answer && <p className="answer">{answer}</p>
          )}
          {answerIntent !== "status" && answerDetails.length > 0 && (
            <ul className="answer-list">
              {answerDetails.map((detail, index) => (
                <li key={`${detail.id || detail.name}-${index}`}>
                  {detail.type === "slack_message" ? (
                    <>
                      <strong>{detail.user}</strong>: {detail.text}
                    </>
                  ) : detail.type === "slack_channel" ? (
                    <>
                      <strong>{detail.name}</strong> ({detail.id}) - {detail.is_private ? "Private" : "Public"}{" "}
                      channel with {detail.members_count} member(s).
                    </>
                  ) : (
                    <>
                      <strong>{detail.name}</strong> is currently <strong>{detail.status}</strong> and owned by{" "}
                      {detail.owner}.
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
      {!error && !answer && answerDetails.length === 0 && (
        <p className="empty-state">Ask a project question to get a natural-language response.</p>
      )}
    </div>
  );
}

export default App;
