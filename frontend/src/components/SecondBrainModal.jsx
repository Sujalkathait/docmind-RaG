import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  X,
  Brain,
  Sparkles,
  BookOpen,
  Trash2,
  Plus,
  Search,
  Download,
  Copy,
  Check,
  CheckCircle2,
  Share2,
  FileText,
  Sliders,
  Network,
  LayoutGrid,
} from 'lucide-react';
import WikiGraphVisualizer from './WikiGraphVisualizer';


export default function SecondBrainModal({
  isOpen,
  onClose,
  initialTab = 'memory', // 'memory' | 'graph' | 'studio'
  api,
  documents,
  folders,
  onStatsUpdate,
}) {
  const [activeTab, setActiveTab] = useState(initialTab);

  // MEMORY STATE
  const [memories, setMemories] = useState([]);
  const [memoryFilter, setMemoryFilter] = useState('all');
  const [isAddingMemory, setIsAddingMemory] = useState(false);
  const [newMemoryCategory, setNewMemoryCategory] = useState('key_fact');
  const [newMemoryContent, setNewMemoryContent] = useState('');
  const [newMemoryImportance, setNewMemoryImportance] = useState(0.8);

  // WIKI GRAPH STATE
  const [graphData, setGraphData] = useState({ nodes: [], edges: [] });
  const [conceptFilter, setConceptFilter] = useState('');
  const [selectedConcept, setSelectedConcept] = useState(null);
  const [graphViewMode, setGraphViewMode] = useState('network'); // 'network' | 'grid'
  const [isMiningGraph, setIsMiningGraph] = useState(false);

  // STUDY STUDIO STATE
  const [deliverableType, setDeliverableType] = useState('notes');
  const [targetDocId, setTargetDocId] = useState('');
  const [targetFolder, setTargetFolder] = useState('General');
  const [customNotes, setCustomNotes] = useState('');
  const [isGeneratingOutput, setIsGeneratingOutput] = useState(false);
  const [generatedOutput, setGeneratedOutput] = useState(null);
  const [recentOutputs, setRecentOutputs] = useState([]);
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setActiveTab(initialTab);
      loadMemories();
      loadGraph();
      loadOutputs();
    }
  }, [isOpen, initialTab]);

  const loadMemories = async () => {
    try {
      const data = await api.getMemories('default_user', memoryFilter);
      setMemories(data.memories || []);
    } catch (e) {
      console.error(e);
    }
  };

  const loadGraph = async () => {
    try {
      const data = await api.getWikiGraph();
      setGraphData(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleMineAll = async () => {
    if (!documents || documents.length === 0) {
      alert('No documents found in vault. Please upload a PDF first.');
      return;
    }
    setIsMiningGraph(true);
    try {
      for (const doc of documents.slice(0, 5)) {
        await api.mineConcepts(doc.id);
      }
      await loadGraph();
      if (onStatsUpdate) onStatsUpdate();
    } catch (err) {
      console.error('Mining error:', err);
    } finally {
      setIsMiningGraph(false);
    }
  };


  const loadOutputs = async () => {
    try {
      const data = await api.getOutputs();
      setRecentOutputs(data.outputs || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleAddMemory = async (e) => {
    e.preventDefault();
    if (!newMemoryContent.trim()) return;
    try {
      await api.addMemory('default_user', newMemoryCategory, newMemoryContent.trim(), newMemoryImportance);
      setNewMemoryContent('');
      setIsAddingMemory(false);
      await loadMemories();
      if (onStatsUpdate) onStatsUpdate();
    } catch (err) {
      alert(`Error adding memory: ${err.message}`);
    }
  };

  const handleDeleteMemory = async (id) => {
    try {
      await api.deleteMemory(id);
      await loadMemories();
      if (onStatsUpdate) onStatsUpdate();
    } catch (err) {
      alert(`Error deleting memory: ${err.message}`);
    }
  };

  const handleGenerateDeliverable = async () => {
    setIsGeneratingOutput(true);
    setGeneratedOutput(null);
    try {
      const res = await api.generateOutput(
        deliverableType,
        targetDocId || null,
        targetFolder,
        null,
        customNotes || null
      );
      setGeneratedOutput(res);
      await loadOutputs();
      if (onStatsUpdate) onStatsUpdate();
    } catch (err) {
      alert(`Generation failed: ${err.message}`);
    } finally {
      setIsGeneratingOutput(false);
    }
  };

  const handleDownloadOutput = () => {
    if (!generatedOutput?.content) return;
    const blob = new Blob([generatedOutput.content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${generatedOutput.title || 'study_deliverable'}.md`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleCopyOutput = () => {
    if (!generatedOutput?.content) return;
    navigator.clipboard.writeText(generatedOutput.content);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  if (!isOpen) return null;

  const filteredConcepts = graphData.nodes?.filter((n) =>
    n.name.toLowerCase().includes(conceptFilter.toLowerCase()) ||
    n.description?.toLowerCase().includes(conceptFilter.toLowerCase())
  ) || [];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        style={{ width: '92%', maxWidth: '1080px', height: '88vh' }}
      >
        {/* Modal Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          backgroundColor: 'var(--bg-glass)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Brain size={18} color="#ffffff" />
            </div>
            <div>
              <h3 style={{ fontSize: '17px', fontWeight: 700 }}>Second Brain Hub</h3>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Persistent Memory, Cross-Document Knowledge Graph, & Deliverables Studio
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {/* Top Hub Tabs */}
            <div style={{
              display: 'flex',
              background: 'rgba(255, 255, 255, 0.04)',
              padding: '3px',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--border-subtle)',
            }}>
              <button
                onClick={() => setActiveTab('memory')}
                className="btn btn-sm"
                style={{
                  background: activeTab === 'memory' ? 'var(--accent-primary)' : 'transparent',
                  color: activeTab === 'memory' ? '#fff' : 'var(--text-secondary)',
                }}
              >
                <Brain size={13} />
                <span>Memory Vault</span>
              </button>

              <button
                onClick={() => setActiveTab('graph')}
                className="btn btn-sm"
                style={{
                  background: activeTab === 'graph' ? 'var(--accent-cyan)' : 'transparent',
                  color: activeTab === 'graph' ? '#fff' : 'var(--text-secondary)',
                }}
              >
                <Sparkles size={13} />
                <span>Wiki Knowledge Graph</span>
              </button>

              <button
                onClick={() => setActiveTab('studio')}
                className="btn btn-sm"
                style={{
                  background: activeTab === 'studio' ? 'var(--accent-emerald)' : 'transparent',
                  color: activeTab === 'studio' ? '#fff' : 'var(--text-secondary)',
                }}
              >
                <BookOpen size={13} />
                <span>Study Studio</span>
              </button>
            </div>

            <button
              onClick={onClose}
              className="btn btn-ghost btn-icon"
              style={{ width: '32px', height: '32px' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
          {/* TAB 1: MEMORY VAULT */}
          {activeTab === 'memory' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ fontSize: '16px', fontWeight: 600 }}>Selective Long-Term Memory</h4>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    Persistent context evaluated by Relevance, Importance, Recency, and Projection score.
                  </div>
                </div>

                <button
                  onClick={() => setIsAddingMemory(!isAddingMemory)}
                  className="btn btn-primary btn-sm"
                >
                  <Plus size={14} />
                  <span>{isAddingMemory ? 'Cancel' : 'Add Memory'}</span>
                </button>
              </div>

              {/* Add Memory Form */}
              {isAddingMemory && (
                <form
                  onSubmit={handleAddMemory}
                  className="glass-panel"
                  style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}
                >
                  <div style={{ display: 'flex', gap: '12px' }}>
                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>
                        Category
                      </label>
                      <select
                        value={newMemoryCategory}
                        onChange={(e) => setNewMemoryCategory(e.target.value)}
                        className="input-control"
                      >
                        <option value="key_fact">Key Fact</option>
                        <option value="user_preference">User Preference</option>
                        <option value="decision">Decision</option>
                        <option value="document_insight">Document Insight</option>
                      </select>
                    </div>

                    <div style={{ flex: 1 }}>
                      <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>
                        Importance Score: {newMemoryImportance}
                      </label>
                      <input
                        type="range"
                        min="0.1"
                        max="1.0"
                        step="0.05"
                        value={newMemoryImportance}
                        onChange={(e) => setNewMemoryImportance(Number(e.target.value))}
                        style={{ width: '100%', accentColor: 'var(--accent-primary)', marginTop: '8px' }}
                      />
                    </div>
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px', display: 'block' }}>
                      Memory Content / Insight
                    </label>
                    <textarea
                      rows={2}
                      value={newMemoryContent}
                      onChange={(e) => setNewMemoryContent(e.target.value)}
                      placeholder="e.g. Always format explanations with architectural trade-offs..."
                      className="input-control"
                      required
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button type="submit" className="btn btn-primary btn-sm">
                      Save to Persistent Memory
                    </button>
                  </div>
                </form>
              )}

              {/* Memory Cards Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(310px, 1fr))', gap: '12px' }}>
                {memories.length === 0 ? (
                  <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '32px', color: 'var(--text-muted)' }}>
                    No memories stored yet. Add memories manually or ask questions to let Second Brain distill key context!
                  </div>
                ) : (
                  memories.map((m) => (
                    <div
                      key={m.id}
                      className="glass-panel"
                      style={{ padding: '14px', display: 'flex', flexDirection: 'column', gap: '8px' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <span className={`badge ${
                          m.category === 'user_preference' ? 'badge-purple' :
                          m.category === 'key_fact' ? 'badge-cyan' :
                          m.category === 'document_insight' ? 'badge-emerald' : 'badge-amber'
                        }`}>
                          {m.category.replace('_', ' ')}
                        </span>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Score: {(m.importance_score || 0.5).toFixed(2)}
                          </span>
                          <button
                            onClick={() => handleDeleteMemory(m.id)}
                            className="btn-ghost"
                            style={{ padding: '2px', border: 'none', cursor: 'pointer' }}
                            title="Delete memory"
                          >
                            <Trash2 size={13} color="var(--text-muted)" />
                          </button>
                        </div>
                      </div>

                      <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: '1.5' }}>
                        {m.content}
                      </div>

                      <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '4px' }}>
                        Accessed: {m.access_count || 0} times
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* TAB 2: WIKI KNOWLEDGE GRAPH */}
          {activeTab === 'graph' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
                <div>
                  <h4 style={{ fontSize: '16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Network size={18} color="var(--accent-cyan)" />
                    <span>Wiki Knowledge Graph & Concept Network</span>
                  </h4>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                    {graphData.nodes?.length || 0} interconnected topics with {graphData.edges?.length || 0} cross-document relationships.
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  {/* View Mode Toggle */}
                  <div style={{
                    display: 'flex',
                    background: 'rgba(0,0,0,0.25)',
                    padding: '3px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                  }}>
                    <button
                      onClick={() => setGraphViewMode('network')}
                      style={{
                        padding: '4px 10px',
                        fontSize: '11px',
                        borderRadius: 'var(--radius-sm)',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        background: graphViewMode === 'network' ? 'var(--accent-cyan)' : 'transparent',
                        color: graphViewMode === 'network' ? '#000' : 'var(--text-secondary)',
                        fontWeight: 600,
                      }}
                    >
                      <Network size={13} />
                      <span>Visual Graph</span>
                    </button>
                    <button
                      onClick={() => setGraphViewMode('grid')}
                      style={{
                        padding: '4px 10px',
                        fontSize: '11px',
                        borderRadius: 'var(--radius-sm)',
                        border: 'none',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '5px',
                        background: graphViewMode === 'grid' ? 'var(--accent-cyan)' : 'transparent',
                        color: graphViewMode === 'grid' ? '#000' : 'var(--text-secondary)',
                        fontWeight: 600,
                      }}
                    >
                      <LayoutGrid size={13} />
                      <span>Cards</span>
                    </button>
                  </div>

                  {/* Mine Concepts Button */}
                  <button
                    onClick={handleMineAll}
                    disabled={isMiningGraph}
                    className="btn btn-secondary btn-sm"
                    style={{ fontSize: '11px', padding: '5px 10px' }}
                    title="Extract Concepts and Relationships from Vault PDFs"
                  >
                    <Sparkles size={13} color="var(--accent-cyan)" />
                    <span>{isMiningGraph ? 'Mining...' : 'Extract Concepts'}</span>
                  </button>

                  {/* Search Bar */}
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    background: 'var(--bg-glass-input)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '5px 10px',
                    width: '180px',
                  }}>
                    <Search size={13} color="var(--text-muted)" style={{ marginRight: '6px' }} />
                    <input
                      type="text"
                      placeholder="Filter concepts..."
                      value={conceptFilter}
                      onChange={(e) => setConceptFilter(e.target.value)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        color: 'var(--text-primary)',
                        fontSize: '12px',
                        outline: 'none',
                        width: '100%',
                      }}
                    />
                  </div>
                </div>
              </div>

              {/* View 1: Interactive Network Graph */}
              {graphViewMode === 'network' && (
                <WikiGraphVisualizer
                  nodes={filteredConcepts}
                  edges={graphData.edges || []}
                  selectedConcept={selectedConcept}
                  onSelectConcept={setSelectedConcept}
                  onMineClick={handleMineAll}
                  isMining={isMiningGraph}
                />
              )}

              {/* View 2: Cards Grid */}
              {graphViewMode === 'grid' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {/* Cross-Domain Relationships Preview */}
                  {graphData.edges && graphData.edges.length > 0 && (
                    <div style={{
                      background: 'rgba(99, 102, 241, 0.08)',
                      border: '1px solid var(--border-glow)',
                      borderRadius: 'var(--radius-md)',
                      padding: '12px 16px',
                    }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Sparkles size={14} />
                        <span>Mined Cross-Domain Relationships:</span>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {graphData.edges.map((edge, idx) => (
                          <div
                            key={idx}
                            style={{
                              fontSize: '11px',
                              background: 'rgba(0, 0, 0, 0.3)',
                              padding: '4px 8px',
                              borderRadius: 'var(--radius-sm)',
                              border: '1px solid var(--border-subtle)',
                            }}
                          >
                            <strong>{edge.source}</strong>
                            <span style={{ color: 'var(--accent-purple)', margin: '0 6px' }}>
                              —[{edge.type || edge.relation_type || 'related_to'}]→
                            </span>
                            <strong>{edge.target}</strong>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Concepts Grid */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '14px' }}>
                    {filteredConcepts.map((node) => (
                      <div
                        key={node.id}
                        className="glass-panel"
                        style={{
                          padding: '16px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '8px',
                          border: selectedConcept?.id === node.id ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                          cursor: 'pointer',
                        }}
                        onClick={() => setSelectedConcept(node)}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                            🌐 {node.name}
                          </span>
                          <span className="badge badge-purple" style={{ fontSize: '9px' }}>
                            {node.category || 'Concept'}
                          </span>
                        </div>

                        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                          {node.definition || node.summary || 'Core concept extracted from indexed library documents.'}
                        </div>

                        {node.aliases && node.aliases.length > 0 && (
                          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            Aliases: {node.aliases.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}


          {/* TAB 3: STUDY STUDIO */}
          {activeTab === 'studio' && (
            <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: '24px' }}>
              {/* Deliverable Config Form */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h4 style={{ fontSize: '16px', fontWeight: 600 }}>Generate Learning Deliverable</h4>

                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
                    Deliverable Format
                  </label>
                  <select
                    value={deliverableType}
                    onChange={(e) => setDeliverableType(e.target.value)}
                    className="input-control"
                  >
                    <option value="notes">📘 Structured Study Notes</option>
                    <option value="summary">📄 Comprehensive Summary</option>
                    <option value="quiz">🎯 Multi-Part Practice Quiz</option>
                    <option value="flashcards">🗂️ Conceptual Flashcards</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
                    Target Document
                  </label>
                  <select
                    value={targetDocId}
                    onChange={(e) => setTargetDocId(e.target.value)}
                    className="input-control"
                  >
                    <option value="">All Documents in Folder</option>
                    {documents.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.filename}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
                    Collection Scope
                  </label>
                  <select
                    value={targetFolder}
                    onChange={(e) => setTargetFolder(e.target.value)}
                    className="input-control"
                  >
                    {folders.map((f) => (
                      <option key={f} value={f}>
                        📁 {f}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px', display: 'block' }}>
                    Custom Focus / Notes (Optional)
                  </label>
                  <textarea
                    rows={3}
                    value={customNotes}
                    onChange={(e) => setCustomNotes(e.target.value)}
                    placeholder="e.g. Emphasize recovery protocols and real-world failure cases..."
                    className="input-control"
                  />
                </div>

                <button
                  onClick={handleGenerateDeliverable}
                  disabled={isGeneratingOutput}
                  className="btn btn-cyan"
                  style={{ justifyContent: 'center' }}
                >
                  <Sparkles size={16} />
                  <span>{isGeneratingOutput ? 'Synthesizing...' : 'Generate Deliverable'}</span>
                </button>

                {/* Past Outputs List */}
                {recentOutputs.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                      Recent Deliverables
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '180px', overflowY: 'auto' }}>
                      {recentOutputs.map((out) => (
                        <div
                          key={out.id}
                          onClick={() => setGeneratedOutput(out)}
                          style={{
                            padding: '8px 10px',
                            borderRadius: 'var(--radius-sm)',
                            background: 'rgba(255, 255, 255, 0.03)',
                            border: '1px solid var(--border-subtle)',
                            cursor: 'pointer',
                            fontSize: '12px',
                          }}
                        >
                          <div style={{ fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {out.title || out.deliverable_type}
                          </div>
                          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                            {out.deliverable_type} • {out.created_at ? new Date(out.created_at).toLocaleDateString() : 'Saved'}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Deliverable Preview Display */}
              <div className="glass-panel" style={{ padding: '20px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                {generatedOutput ? (
                  <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      paddingBottom: '12px',
                      borderBottom: '1px solid var(--border-subtle)',
                      marginBottom: '14px',
                    }}>
                      <div>
                        <h4 style={{ fontSize: '16px', fontWeight: 700 }}>
                          {generatedOutput.title || 'Generated Deliverable'}
                        </h4>
                        <span className="badge badge-emerald" style={{ fontSize: '10px', marginTop: '4px' }}>
                          {generatedOutput.deliverable_type}
                        </span>
                      </div>

                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button onClick={handleCopyOutput} className="btn btn-secondary btn-sm">
                          {isCopied ? <Check size={13} color="var(--accent-emerald)" /> : <Copy size={13} />}
                          <span>{isCopied ? 'Copied' : 'Copy'}</span>
                        </button>
                        <button onClick={handleDownloadOutput} className="btn btn-cyan btn-sm">
                          <Download size={13} />
                          <span>Export .md</span>
                        </button>
                      </div>
                    </div>

                    <div style={{ flex: 1, overflowY: 'auto', paddingRight: '6px' }} className="markdown-body">
                      <ReactMarkdown>{generatedOutput.content}</ReactMarkdown>
                    </div>
                  </div>
                ) : (
                  <div style={{
                    height: '100%',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--text-muted)',
                    textAlign: 'center',
                    gap: '12px',
                  }}>
                    <BookOpen size={36} color="var(--border-subtle)" />
                    <div style={{ fontSize: '14px' }}>
                      Select options and click "Generate Deliverable" to craft study materials from your Second Brain.
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
