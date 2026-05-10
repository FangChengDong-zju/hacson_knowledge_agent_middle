import { useState } from "react";
import { api } from "../api";
import type { IntegrationDecision, RAGAnswer } from "../types";

interface Props {
  decisions: IntegrationDecision[];
  onDecisionUpdated: () => Promise<void>;
}

export default function QAWorkspace({ decisions, onDecisionUpdated }: Props) {
  const [question, setQuestion] = useState("");
  const [feedback, setFeedback] = useState("");
  const [answer, setAnswer] = useState<RAGAnswer | null>(null);
  const [reply, setReply] = useState("");

  async function ask() {
    if (!question.trim()) return;
    setAnswer(await api.ask(question));
  }

  async function sendFeedback() {
    if (!feedback.trim()) return;
    const target = decisions[0]?.decision_id;
    const result = await api.feedback(feedback, target);
    setReply(result.reply);
    await onDecisionUpdated();
  }

  return (
    <aside className="right-panel">
      <section className="panel qa-panel">
        <h2>RAG 问答</h2>
        <textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="输入教材相关问题" />
        <button onClick={ask}>带引用回答</button>
        {answer && (
          <div className="answer-box">
            <p>{answer.answer}</p>
            <h3>引用来源</h3>
            {answer.citations.map((citation, index) => (
              <article className="citation" key={`${citation.chunk_id}_${index}`}>
                <strong>{citation.textbook}</strong>
                <span>{citation.chapter} · {citation.page ?? "页码待识别"} · {citation.relevance_score}</span>
                <p>{citation.source_text}</p>
              </article>
            ))}
          </div>
        )}
      </section>
      <section className="panel qa-panel">
        <h2>教师反馈</h2>
        <textarea value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="例如：请保留免疫应答，不要删除" />
        <button onClick={sendFeedback}>修改整合决策</button>
        {reply && <p className="reply">{reply}</p>}
      </section>
    </aside>
  );
}

