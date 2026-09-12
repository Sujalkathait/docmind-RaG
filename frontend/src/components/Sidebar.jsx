import React, { useState } from 'react';
import {
  MessageSquarePlus,
  MessageSquare,
  FileText,
  UploadCloud,
  Trash2,
  Cpu,
  Sparkles,
  Sliders,
  CheckCircle2,
  AlertCircle,
  Database,
  Brain,
  Layers,
  ChevronRight,
} from 'lucide-react';

export default function Sidebar({
  sessions,
  currentSessionId,
  onSelectSession,
  onNewChat,
  documents,
  folders,
  selectedFolder,
  onUploadSuccess,
  onMineSuccess,
  api,
  isCollapsed,
  onToggleCollapse,
  settings,
  onUpdateSettings,
  stats,
  onDeleteSession,
}) {
  const [activeTab, setActiveTab] = useState('chats'); // 'chats' | 'vault' | 'settings'
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [targetFolder, setTargetFolder] = useState('General');
  const [miningDocId, setMiningDocId] = useState(null);

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const res = await api.uploadDocument(file, targetFolder);
      setUploadSuccess(`Ingested ${res.total_chunks} chunks from ${res.filename}!`);
      if (onUploadSuccess) onUploadSuccess(res);
      setTimeout(() => setUploadSuccess(null), 4000);
    } catch (err) {
      setUploadError(err.message || 'Upload failed');
    } finally {
      setIsUploading(false);
      e.target.value = '';
    }
  };

  const handleMineConcepts = async (docId) => {
    setMiningDocId(docId);
    try {
      const res = await api.mineConcepts(docId);
      if (onMineSuccess) onMineSuccess(res);
    } catch (err) {
      alert(`Concept mining failed: ${err.message}`);
    } finally {
      setMiningDocId(null);
    }
  };

  const handleDeleteDoc = async (docId) => {
    if (!window.confirm('Delete this document and its chunk vectors from Second Brain?')) return;
    try {
      await api.deleteDocument(docId);
      if (onUploadSuccess) onUploadSuccess();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  return (
    <aside style={{
      width: isCollapsed ? '60px' : '320px',
      height: 'calc(100vh - 64px)',
      backgroundColor: 'var(--bg-secondary)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      transition: 'width var(--transition-normal)',
      overflow: 'hidden',
      position: 'relative',
      zIndex: 50,
    }}>
      {/* Top Action / New Chat */}
      <div style={{ padding: '16px', borderBottom: '1px solid var(--border-subtle)' }}>
        {!isCollapsed ? (
          <button
            className="btn btn-primary"
            style={{ width: '100%', justifyContent: 'center' }}
            onClick={onNewChat}
          >
            <MessageSquarePlus size={18} />
            <span>New Chat Session</span>
          </button>
        ) : (
          <button
            className="btn btn-primary btn-icon"
            style={{ margin: '0 auto', display: 'flex' }}
            onClick={onNewChat}
            title="New Chat Session"
          >
            <MessageSquarePlus size={18} />
          </button>
        )}
      </div>

      {/* Navigation Tab Bar */}
      {!isCollapsed && (
        <div style={{
          display: 'flex',
          padding: '8px 12px',
          gap: '6px',
          borderBottom: '1px solid var(--border-subtle)',
          backgroundColor: 'rgba(0,0,0,0.15)',
        }}>
          <button
            onClick={() => setActiveTab('chats')}
            style={{
              flex: 1,
              padding: '6px',
              fontSize: '12px',
              fontWeight: 500,
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              background: activeTab === 'chats' ? 'rgba(255,255,255,0.08)' : 'transparent',
              color: activeTab === 'chats' ? 'var(--text-primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <MessageSquare size={14} />
            Chats
          </button>

          <button
            onClick={() => setActiveTab('vault')}
            style={{
              flex: 1,
              padding: '6px',
              fontSize: '12px',
              fontWeight: 500,
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              background: activeTab === 'vault' ? 'rgba(255,255,255,0.08)' : 'transparent',
              color: activeTab === 'vault' ? 'var(--text-primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <Database size={14} />
            Vault ({documents.length})
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            style={{
              flex: 1,
              padding: '6px',
              fontSize: '12px',
              fontWeight: 500,
              borderRadius: 'var(--radius-sm)',
              border: 'none',
              background: activeTab === 'settings' ? 'rgba(255,255,255,0.08)' : 'transparent',
              color: activeTab === 'settings' ? 'var(--text-primary)' : 'var(--text-muted)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <Sliders size={14} />
            Config
          </button>
        </div>
      )}

      {/* Main Tab Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: isCollapsed ? '8px' : '16px' }}>
        {/* TAB: CHATS */}
        {activeTab === 'chats' && !isCollapsed && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
              Recent Conversations
            </div>
            {sessions.length === 0 ? (
              <div style={{ fontSize: '13px', color: 'var(--text-muted)', fontStyle: 'italic', padding: '12px 0' }}>
                No past sessions yet. Start a new query!
              </div>
            ) : (
              sessions.map((sess) => (
                <div
                  key={sess.id}
                  onClick={() => onSelectSession(sess.id)}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-md)',
                    background: currentSessionId === sess.id ? 'rgba(99, 102, 241, 0.15)' : 'rgba(255, 255, 255, 0.02)',
                    border: currentSessionId === sess.id ? '1px solid var(--accent-primary)' : '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '6px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden', flex: 1 }}>
                    <MessageSquare size={15} color={currentSessionId === sess.id ? 'var(--accent-cyan)' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
                    <span style={{
                      fontSize: '12px',
                      color: currentSessionId === sess.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }} title={sess.title || sess.id}>
                      {sess.title || sess.id}
                    </span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (window.confirm(`Delete conversation "${sess.title || sess.id}"?`)) {
                        if (onDeleteSession) onDeleteSession(sess.id);
                      }
                    }}
                    className="btn-ghost"
                    style={{
                      padding: '3px',
                      border: 'none',
                      background: 'transparent',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      opacity: 0.6,
                      borderRadius: 'var(--radius-sm)',
                      flexShrink: 0,
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = '0.6'}
                    title="Delete Conversation"
                  >
                    <Trash2 size={13} color="var(--accent-rose, #f43f5e)" />
                  </button>
                </div>
              ))
            )}
          </div>
        )}

        {/* TAB: VAULT (Documents & Upload) */}
        {activeTab === 'vault' && !isCollapsed && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Upload Box */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px dashed var(--border-glow)',
              borderRadius: 'var(--radius-md)',
              padding: '16px',
              textAlign: 'center',
            }}>
              <UploadCloud size={24} color="var(--accent-cyan)" style={{ margin: '0 auto 8px' }} />
              <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '4px' }}>
                Upload PDF Document
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                Auto-chunks, embeds, and indexes to ChromaDB
              </div>

              {/* Folder Target */}
              <div style={{ display: 'flex', gap: '6px', marginBottom: '10px' }}>
                <input
                  type="text"
                  placeholder="Folder/Collection..."
                  value={targetFolder}
                  onChange={(e) => setTargetFolder(e.target.value)}
                  className="input-control"
                  style={{ fontSize: '12px', padding: '6px 10px' }}
                />
              </div>

              <label className="btn btn-secondary btn-sm" style={{ width: '100%', cursor: isUploading ? 'not-allowed' : 'pointer' }}>
                {isUploading ? 'Ingesting PDF...' : 'Choose PDF File'}
                <input
                  type="file"
                  accept=".pdf"
                  onChange={handleFileUpload}
                  disabled={isUploading}
                  style={{ display: 'none' }}
                />
              </label>

              {uploadSuccess && (
                <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--accent-emerald)', display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}>
                  <CheckCircle2 size={13} />
                  <span>{uploadSuccess}</span>
                </div>
              )}
              {uploadError && (
                <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--accent-rose)', display: 'flex', alignItems: 'center', gap: '4px', justifyContent: 'center' }}>
                  <AlertCircle size={13} />
                  <span>{uploadError}</span>
                </div>
              )}
            </div>

            {/* Document List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Indexed Documents ({documents.length})
              </div>
              {documents.length === 0 ? (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  No documents found in selected folder.
                </div>
              ) : (
                documents.map((doc) => (
                  <div
                    key={doc.id}
                    style={{
                      padding: '10px',
                      borderRadius: 'var(--radius-md)',
                      background: 'rgba(255, 255, 255, 0.02)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', overflow: 'hidden' }}>
                        <FileText size={14} color="var(--accent-cyan)" />
                        <span style={{
                          fontSize: '12px',
                          fontWeight: 500,
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          maxWidth: '180px',
                        }} title={doc.filename}>
                          {doc.filename}
                        </span>
                      </div>
                      <button
                        onClick={() => handleDeleteDoc(doc.id)}
                        className="btn-ghost"
                        style={{ padding: '2px', border: 'none', cursor: 'pointer' }}
                        title="Delete Document"
                      >
                        <Trash2 size={13} color="var(--text-muted)" />
                      </button>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <span className="badge badge-cyan" style={{ fontSize: '9px', padding: '1px 5px' }}>
                          {doc.total_chunks || 0} chunks
                        </span>
                        <span className="badge badge-purple" style={{ fontSize: '9px', padding: '1px 5px' }}>
                          {doc.folder}
                        </span>
                      </div>

                      <button
                        onClick={() => handleMineConcepts(doc.id)}
                        disabled={miningDocId === doc.id}
                        className="btn btn-ghost btn-sm"
                        style={{ fontSize: '11px', padding: '2px 6px', color: 'var(--accent-cyan)' }}
                        title="Extract Wiki Concepts from this PDF"
                      >
                        <Sparkles size={12} />
                        {miningDocId === doc.id ? 'Mining...' : 'Mine Wiki'}
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* TAB: CONFIG / SETTINGS */}
        {activeTab === 'settings' && !isCollapsed && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              RAG & Second Brain Hyperparameters
            </div>

            {/* Context Budget */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Context Budget (Tokens)</span>
                <span style={{ color: 'var(--accent-cyan)', fontWeight: 600 }}>{settings.contextBudget}</span>
              </div>
              <input
                type="range"
                min="2048"
                max="8192"
                step="512"
                value={settings.contextBudget}
                onChange={(e) => onUpdateSettings({ ...settings, contextBudget: Number(e.target.value) })}
                style={{ width: '100%', accentColor: 'var(--accent-cyan)' }}
              />
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Safe threshold prevents local llama.cpp memory overflows.
              </div>
            </div>

            {/* Retrieval Top-K */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Top-K Retrieval</span>
                <span style={{ color: 'var(--accent-purple)', fontWeight: 600 }}>{settings.topK} chunks</span>
              </div>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={settings.topK}
                onChange={(e) => onUpdateSettings({ ...settings, topK: Number(e.target.value) })}
                style={{ width: '100%', accentColor: 'var(--accent-purple)' }}
              />
            </div>

            {/* LLM Temperature */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                <span style={{ color: 'var(--text-secondary)' }}>Temperature</span>
                <span style={{ color: 'var(--accent-emerald)', fontWeight: 600 }}>{settings.temperature}</span>
              </div>
              <input
                type="range"
                min="0.0"
                max="1.0"
                step="0.05"
                value={settings.temperature}
                onChange={(e) => onUpdateSettings({ ...settings, temperature: Number(e.target.value) })}
                style={{ width: '100%', accentColor: 'var(--accent-emerald)' }}
              />
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Lower values guarantee deterministic, hallucination-free grounded answers.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Footer Second Brain Metrics */}
      {!isCollapsed && stats && (
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border-subtle)',
          backgroundColor: 'rgba(0,0,0,0.2)',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '8px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Sparkles size={13} color="var(--accent-cyan)" />
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {stats.conceptsCount || 0} Wiki Nodes
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Brain size={13} color="var(--accent-purple)" />
            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              {stats.memoriesCount || 0} Memories
            </span>
          </div>
        </div>
      )}
    </aside>
  );
}
