import React, { useState, useEffect } from 'react';
import { api } from './api';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import SecondBrainModal from './components/SecondBrainModal';

export default function App() {
  // System Telemetry
  const [health, setHealth] = useState(null);

  // Scoping & Documents
  const [folders, setFolders] = useState(['General']);
  const [selectedFolder, setSelectedFolder] = useState('All Collections');
  const [documents, setDocuments] = useState([]);

  // Chat State
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(() => `session_${Date.now()}`);
  const [messages, setMessages] = useState([]);
  const [isGenerating, setIsGenerating] = useState(false);

  // Second Brain Modal
  const [isBrainModalOpen, setIsBrainModalOpen] = useState(false);
  const [brainModalInitialTab, setBrainModalInitialTab] = useState('memory');

  // Sidebar Layout
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  // Hyperparameters
  const [settings, setSettings] = useState({
    contextBudget: 4096,
    topK: 4,
    temperature: 0.2,
  });

  // Second Brain Stats
  const [stats, setStats] = useState({
    conceptsCount: 0,
    memoriesCount: 0,
    outputsCount: 0,
  });

  // Initial Load
  useEffect(() => {
    refreshAllData();

    // Poll health status periodically
    const interval = setInterval(async () => {
      const h = await api.getHealth();
      setHealth(h);
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  // Reload documents when folder changes
  useEffect(() => {
    loadDocuments();
  }, [selectedFolder]);

  const refreshAllData = async () => {
    try {
      const [h, f, docs, sess, graph, mems] = await Promise.all([
        api.getHealth(),
        api.getFolders(),
        api.getDocuments(selectedFolder),
        api.getSessions(),
        api.getWikiGraph().catch(() => ({ nodes: [] })),
        api.getMemories('default_user').catch(() => ({ memories: [] })),
      ]);

      setHealth(h);
      if (f && f.length > 0) setFolders(f);
      setDocuments(docs.documents || []);
      setSessions(sess.sessions || []);
      setStats({
        conceptsCount: graph.nodes?.length || 0,
        memoriesCount: mems.memories?.length || 0,
        outputsCount: 0,
      });
    } catch (err) {
      console.error('Data initialization error:', err);
    }
  };

  const loadDocuments = async () => {
    try {
      const res = await api.getDocuments(selectedFolder);
      setDocuments(res.documents || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleNewChat = () => {
    const newId = `session_${Date.now()}`;
    setCurrentSessionId(newId);
    setMessages([]);
    setSessions((prev) => [{ id: newId, title: 'New Conversation', created_at: new Date().toISOString() }, ...prev]);
  };

  const handleSelectSession = async (sessId) => {
    setCurrentSessionId(sessId);
    try {
      const hist = await api.getChatHistory(sessId);
      if (hist && Array.isArray(hist)) {
        setMessages(hist.map((item) => ({
          role: item.role,
          content: item.content,
          metadata: item.metadata,
        })));
      }
    } catch (err) {
      console.error('Failed to load session history:', err);
    }
  };

  const handleDeleteSession = async (sessionId) => {
    try {
      await api.deleteSession(sessionId);
      const remaining = sessions.filter((s) => s.id !== sessionId);
      setSessions(remaining);
      if (currentSessionId === sessionId) {
        if (remaining.length > 0) {
          handleSelectSession(remaining[0].id);
        } else {
          handleNewChat();
        }
      }
    } catch (err) {
      alert(`Failed to delete conversation: ${err.message}`);
    }
  };

  const handleSendMessage = async (query) => {
    if (!query.trim() || isGenerating) return;

    // Append user message immediately
    const userMsg = { role: 'user', content: query };
    const assistantPlaceholder = { role: 'assistant', content: '', metadata: null };

    setMessages((prev) => [...prev, userMsg, assistantPlaceholder]);
    setIsGenerating(true);

    try {
      await api.streamChat({
        query,
        folder: selectedFolder,
        sessionId: currentSessionId,
        userId: 'default_user',
        onChunk: (delta, fullText) => {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: fullText,
              };
            }
            return updated;
          });
        },
        onDone: (fullText, metadata) => {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: fullText,
                metadata,
              };
            }
            return updated;
          });
          setIsGenerating(false);
          refreshAllData(); // Refresh to catch auto-distilled memories
        },
        onError: (err) => {
          setMessages((prev) => {
            const updated = [...prev];
            const lastIdx = updated.length - 1;
            if (lastIdx >= 0 && updated[lastIdx].role === 'assistant') {
              updated[lastIdx] = {
                ...updated[lastIdx],
                content: `⚠️ Error communicating with DocMind API: ${err.message}`,
              };
            }
            return updated;
          });
          setIsGenerating(false);
        },
      });
    } catch (e) {
      setIsGenerating(false);
    }
  };

  const handleSaveToMemory = async (content) => {
    try {
      await api.addMemory('default_user', 'document_insight', content.slice(0, 300), 0.85);
      alert('Saved key insight to Second Brain memory!');
      refreshAllData();
    } catch (e) {
      alert(`Error saving memory: ${e.message}`);
    }
  };

  const handleSwitchModel = async (modelName) => {
    try {
      await api.switchModel(modelName);
      const h = await api.getHealth();
      setHealth(h);
    } catch (e) {
      alert(`Model switch failed: ${e.message}`);
    }
  };

  const openSecondBrain = (tab = 'memory') => {
    setBrainModalInitialTab(tab);
    setIsBrainModalOpen(true);
  };

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top App Header */}
      <Header
        health={health}
        folders={folders}
        selectedFolder={selectedFolder}
        onSelectFolder={setSelectedFolder}
        onOpenSecondBrain={(tab) => openSecondBrain(tab)}
        onOpenStudyStudio={() => openSecondBrain('studio')}
        documentCount={documents.length}
        onSwitchModel={handleSwitchModel}
      />

      {/* Main Workspace Layout */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={handleSelectSession}
          onNewChat={handleNewChat}
          documents={documents}
          folders={folders}
          selectedFolder={selectedFolder}
          onUploadSuccess={loadDocuments}
          onMineSuccess={refreshAllData}
          api={api}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          settings={settings}
          onUpdateSettings={setSettings}
          stats={stats}
          onDeleteSession={handleDeleteSession}
        />

        <ChatView
          messages={messages}
          onSendMessage={handleSendMessage}
          isGenerating={isGenerating}
          selectedFolder={selectedFolder}
          onSaveToMemory={handleSaveToMemory}
        />
      </div>

      {/* Second Brain Hub Modal */}
      <SecondBrainModal
        isOpen={isBrainModalOpen}
        onClose={() => setIsBrainModalOpen(false)}
        initialTab={brainModalInitialTab}
        api={api}
        documents={documents}
        folders={folders}
        onStatsUpdate={refreshAllData}
      />
    </div>
  );
}
