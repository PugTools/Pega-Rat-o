"use client";

import { Send } from "lucide-react";
import { FormEvent, useState } from "react";
import { api } from "@/lib/api";

type Message = {
  role: "user" | "assistant";
  content: string;
};

export function CopilotChat() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Envie uma pergunta sobre alertas, contratos, fornecedores ou conexoes.",
    },
  ]);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) {
      return;
    }

    setMessages((current) => [...current, { role: "user", content: trimmed }]);
    setQuestion("");
    setLoading(true);

    try {
      const response = await api.askCopilot(trimmed);
      setMessages((current) => [
        ...current,
        { role: "assistant", content: response.answer || "Sem resposta disponivel." },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content:
            "Nao foi possivel consultar o copiloto. Verifique autenticacao e disponibilidade da API.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="max-h-80 space-y-3 overflow-y-auto pr-1">
        {messages.map((message, index) => (
          <div
            className={
              message.role === "user"
                ? "ml-auto max-w-[85%] rounded-lg bg-slate-900 px-3 py-2 text-sm text-white dark:bg-white dark:text-slate-950"
                : "max-w-[85%] rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-700 dark:bg-slate-900 dark:text-slate-200"
            }
            key={`${message.role}-${index}`}
          >
            {message.content}
          </div>
        ))}
      </div>

      <form className="flex flex-col gap-2 sm:flex-row" onSubmit={handleSubmit}>
        <input
          className="min-w-0 flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white"
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ex: Quais fornecedores concentram maior risco?"
          value={question}
        />
        <button
          className="inline-flex items-center justify-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-white dark:text-slate-950"
          disabled={loading}
          type="submit"
        >
          <Send className="h-4 w-4" />
          {loading ? "Consultando..." : "Enviar"}
        </button>
      </form>
    </div>
  );
}
