import React, { useState } from 'react';
import { Send, Upload, Link as LinkIcon, FileText, Loader2, Menu, X } from 'lucide-react';

interface Message {
  sender: 'user' | 'bot';
  text: string;
}

export default function App() {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  // États UI
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Message d'accueil explicatif adaptatif
  const welcomeText = "Bonjour ! Je suis Cosmo.\n\nPour commencer, ouvrez le menu en haut à gauche (☰) si vous êtes sur mobile pour charger un document PDF/Word ou une API, puis posez-moi vos questions !";

  const [messages, setMessages] = useState<Message[]>([
    { sender: 'bot', text: welcomeText }
  ]);
  const [query, setQuery] = useState('');
  const [loadingQuery, setLoadingQuery] = useState(false);

  // États des Ingestions
  const [file, setFile] = useState<File | null>(null);
  const [apiUrl, setApiUrl] = useState('');
  const [textKey, setTextKey] = useState('');
  const [statusMsg, setStatusMsg] = useState('');
  const [loadingIngest, setLoadingIngest] = useState(false);

  const handleSendQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    const userText = query;
    setMessages((prev) => [...prev, { sender: 'user', text: userText }]);
    setQuery('');
    setLoadingQuery(true);

    try {
      const res = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: userText, top_k: 3 }),
      });
      const data = await res.json();

      if (!res.ok) throw new Error(data.detail || 'Erreur serveur');

      // Ajout de la réponse SANS les sources
      setMessages((prev) => [
        ...prev,
        { sender: 'bot', text: data.answer }
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { sender: 'bot', text: `Erreur : ${err.message}` }
      ]);
    } finally {
      setLoadingQuery(false);
    }
  };

  const handleIngestFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    setLoadingIngest(true);
    setStatusMsg('');

    try {
      const res = await fetch(`${API_URL}/ingest/file`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setStatusMsg(`Fichier "${file.name}" indexé avec succès ! Vous pouvez poser vos questions.`);
      setFile(null);
      setSidebarOpen(false); // Ferme automatiquement le menu mobile après l'envoi
    } catch (err: any) {
      setStatusMsg(`Erreur : ${err.message}`);
    } finally {
      setLoadingIngest(false);
    }
  };

  const handleIngestAPI = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiUrl) return;

    setLoadingIngest(true);
    setStatusMsg('');

    try {
      const res = await fetch(`${API_URL}/ingest/api`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: apiUrl, text_key: textKey || undefined }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setStatusMsg('API externe indexée avec succès ! Vous pouvez poser vos questions.');
      setApiUrl('');
      setTextKey('');
      setSidebarOpen(false); // Ferme automatiquement le menu mobile après l'envoi
    } catch (err: any) {
      setStatusMsg(`Erreur : ${err.message}`);
    } finally {
      setLoadingIngest(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-900 text-slate-100 font-sans overflow-hidden">
      {/* Overlay Mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Panneau de Gauche : Ingestion */}
      <aside
        className={`fixed md:static inset-y-0 left-0 z-50 w-80 bg-slate-950 border-r border-slate-800 p-4 flex flex-col gap-6 transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/artur-bot.png" alt="Bot Logo" className="w-10 h-10 rounded-full object-cover border-2 border-[#E6007E]" />
            <h1 className="text-xl font-bold text-[#E6007E]">Cosmo RAG</h1>
          </div>
          <button
            className="md:hidden text-slate-400 hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {statusMsg && (
          <div className="p-3 text-xs rounded bg-slate-900 border border-[#E6007E]/40 text-fuchsia-200">
            {statusMsg}
          </div>
        )}

        {/* Formulaire Fichier */}
        <form onSubmit={handleIngestFile} className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-400 flex items-center gap-1">
            <FileText className="w-4 h-4" /> Charger un document
          </h2>
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full text-xs text-slate-400 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-[#E6007E] file:text-white hover:file:bg-[#c4006c] cursor-pointer"
          />
          <button
            type="submit"
            disabled={!file || loadingIngest}
            className="w-full py-2 bg-[#E6007E] hover:bg-[#c4006c] disabled:opacity-50 text-xs font-semibold rounded flex items-center justify-center gap-2 text-white transition-colors"
          >
            {loadingIngest ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} Indexer le fichier
          </button>
        </form>

        <hr className="border-slate-800" />

        {/* Formulaire API */}
        <form onSubmit={handleIngestAPI} className="space-y-3">
          <h2 className="text-sm font-semibold text-slate-400 flex items-center gap-1">
            <LinkIcon className="w-4 h-4" /> Indexer une API REST
          </h2>
          <input
            type="url"
            placeholder="URL de l'API (ex: JSON)"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full p-2.5 text-xs bg-slate-900 border border-slate-800 rounded text-slate-200 focus:outline-none focus:border-[#E6007E]"
          />
          <input
            type="text"
            placeholder="Clé texte optionnelle (ex: body)"
            value={textKey}
            onChange={(e) => setTextKey(e.target.value)}
            className="w-full p-2.5 text-xs bg-slate-900 border border-slate-800 rounded text-slate-200 focus:outline-none focus:border-[#E6007E]"
          />
          <button
            type="submit"
            disabled={!apiUrl || loadingIngest}
            className="w-full py-2 bg-[#E6007E] hover:bg-[#c4006c] disabled:opacity-50 text-xs font-semibold rounded flex items-center justify-center gap-2 text-white transition-colors"
          >
            {loadingIngest ? <Loader2 className="w-4 h-4 animate-spin" /> : <LinkIcon className="w-4 h-4" />} Indexer l'API
          </button>
        </form>
      </aside>

      {/* Zone Principale Chat */}
      <main className="flex-1 flex flex-col h-full w-full bg-slate-900">
        {/* Header Mobile */}
        <header className="md:hidden flex items-center justify-between p-4 bg-slate-950 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <img src="/artur-bot.png" alt="Bot Logo" className="w-8 h-8 rounded-full border border-[#E6007E]" />
            <span className="font-bold text-[#E6007E] text-sm">Cosmo RAG</span>
          </div>
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 text-slate-300 hover:text-white flex items-center gap-1 text-xs border border-slate-800 rounded-lg bg-slate-900"
          >
            <Menu className="w-5 h-5 text-[#E6007E]" />
            <span>Charger document</span>
          </button>
        </header>

        {/* Historique des Messages */}
        {/* Historique des Messages */}
        <div className="flex-1 p-4 md:p-6 overflow-y-auto space-y-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex items-start gap-3 ${
                m.sender === 'user' ? 'flex-row-reverse' : ''
              }`}
            >
              {m.sender === 'user' ? (
                <img
                  src="/utilisateur.png"
                  alt="Utilisateur"
                  className="w-12 h-12 rounded-full object-cover border border-[#E6007E] shrink-0"
                />
              ) : (
                <img
                  src="/artur-bot.png"
                  alt="Bot"
                  className="w-12 h-12 rounded-full object-cover border border-[#E6007E] shrink-0"
                />
              )}

              <div
                className={`max-w-[85%] md:max-w-xl p-4 rounded-2xl text-sm leading-relaxed ${
                  m.sender === 'user'
                    ? 'bg-[#E6007E] text-white rounded-tr-none'
                    : 'bg-slate-800 text-slate-100 border border-slate-700/60 rounded-tl-none shadow-md'
                }`}
              >
                <p className="whitespace-pre-wrap">{m.text}</p>
              </div>
            </div>
          ))}
          {loadingQuery && (
            <div className="flex items-center gap-2 text-xs text-fuchsia-400 italic">
              <Loader2 className="w-4 h-4 animate-spin" /> Cosmo réfléchit...
            </div>
          )}
        </div>

        {/* Barre de saisie */}
        <footer className="p-3 md:p-4 border-t border-slate-800 bg-slate-950">
          <form onSubmit={handleSendQuery} className="flex gap-2 max-w-4xl mx-auto">
            <input
              type="text"
              placeholder="Posez votre question à Cosmo..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="flex-1 p-3 text-sm bg-slate-900 border border-slate-800 rounded-xl text-slate-100 focus:outline-none focus:border-[#E6007E] transition-colors"
            />
            <button
              type="submit"
              disabled={loadingQuery || !query.trim()}
              className="px-4 md:px-5 py-3 bg-[#E6007E] hover:bg-[#c4006c] disabled:opacity-50 text-white rounded-xl flex items-center justify-center transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </footer>
      </main>
    </div>
  );
}