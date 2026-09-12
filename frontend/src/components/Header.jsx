import React from 'react';
import { Brain, Cpu, Database, Sparkles, BookOpen, Layers } from 'lucide-react';

export default function Header({
  health,
  folders,
  selectedFolder,
  onSelectFolder,
  onOpenSecondBrain,
  activeBrainTab,
  onOpenStudyStudio,
  documentCount = 0,
  onSwitchModel,
}) {
  const isOnline = health?.status === 'healthy';
  const modelName = health?.active_model || 'Loading LLM...';
  const gpuLayers = health?.gpu_layers ?? 0;

  return (
    <header style={{
      height: '64px',
      borderBottom: '1px solid var(--border-subtle)',
      backgroundColor: 'var(--bg-glass)',
      backdropFilter: 'blur(12px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 24px',
      zIndex: 100,
      position: 'relative'
    }}>
      {/* Brand & Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '38px',
          height: '38px',
          borderRadius: 'var(--radius-md)',
          background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 0 16px rgba(99, 102, 241, 0.4)',
        }}>
          <Brain size={22} color="#ffffff" />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              fontFamily: 'var(--font-heading)',
              fontSize: '18px',
              fontWeight: 700,
              letterSpacing: '-0.02em',
              background: 'linear-gradient(to right, #ffffff, #cbd5e1)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}>
              DocMind RAG
            </span>
            <span className="badge badge-purple" style={{ fontSize: '10px' }}>
              Second Brain
            </span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Document Intelligence & Persistent Memory
          </div>
        </div>
      </div>

      {/* Center Scope Selector */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '4px 12px',
        }}>
          <Layers size={15} color="var(--accent-cyan)" />
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Scope:</span>
          <select
            value={selectedFolder}
            onChange={(e) => onSelectFolder(e.target.value)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-body)',
              fontSize: '13px',
              fontWeight: 500,
              outline: 'none',
              cursor: 'pointer',
            }}
          >
            <option value="All Collections" style={{ background: '#0f172a' }}>
              All Collections ({documentCount} docs)
            </option>
            {folders.map((f) => (
              <option key={f} value={f} style={{ background: '#0f172a' }}>
                📁 {f}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Right Controls & Health */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        {/* Hub Buttons */}
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => onOpenSecondBrain('graph')}
          title="Open Second Brain Wiki Knowledge Graph & Concepts"
        >
          <Sparkles size={14} color="var(--accent-cyan)" />
          <span>Wiki Graph</span>
        </button>

        <button
          className="btn btn-secondary btn-sm"
          onClick={() => onOpenSecondBrain('memory')}
          title="Open Selective Long-Term Memory Vault"
        >
          <Brain size={14} color="var(--accent-purple)" />
          <span>Memory Vault</span>
        </button>

        <button
          className="btn btn-cyan btn-sm"
          onClick={onOpenStudyStudio}
          title="Open Deliverables Studio (Notes, Quizzes, Summaries)"
        >
          <BookOpen size={14} />
          <span>Study Studio</span>
        </button>

        {/* System Telemetry & Model Switcher Pill */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '4px 10px',
          borderRadius: 'var(--radius-full)',
          background: 'rgba(255, 255, 255, 0.04)',
          border: '1px solid var(--border-subtle)',
          fontSize: '12px',
        }}>
          <span className={`pulsing-dot ${isOnline ? 'online' : 'offline'}`} />
          <Cpu size={14} color="var(--accent-cyan)" />
          {health?.available_models && health.available_models.length > 1 ? (
            <select
              value={modelName}
              onChange={(e) => onSwitchModel && onSwitchModel(e.target.value)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                fontSize: '12px',
                fontFamily: 'var(--font-body)',
                outline: 'none',
                cursor: 'pointer',
                maxWidth: '160px',
              }}
              title="Click to switch local model"
            >
              {health.available_models.map((m) => (
                <option key={m.name} value={m.name} style={{ background: '#0f172a' }}>
                  {m.name} ({m.size_str})
                </option>
              ))}
            </select>
          ) : (
            <span style={{ color: 'var(--text-secondary)', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {modelName}
            </span>
          )}
          {gpuLayers > 0 && (
            <span className="badge badge-cyan" style={{ fontSize: '9px', padding: '1px 5px' }}>
              GPU {gpuLayers}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
