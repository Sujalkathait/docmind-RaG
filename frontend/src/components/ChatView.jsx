import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Send,
  Sparkles,
  Bot,
  User,
  Copy,
  Check,
  BookmarkPlus,
  ChevronDown,
  ChevronUp,
  FileText,
  Brain,
  Layers,
  HelpCircle,
  BookOpen,
} from 'lucide-react';

export default function ChatView({
  messages,
  onSendMessage,
  isGenerating,
  selectedFolder,
  onSaveToMemory,
}) {
  const [inputQuery, setInputQuery] = useState('');
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [expandedContextIndex, setExpandedContextIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isGenerating]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    const query = inputQuery.trim();
    if (!query || isGenerating) return;
    onSendMessage(query);
    setInputQuery('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const starterPrompts = [
    {
      title: 'Analyze Core Concepts',
      desc: 'Synthesize the foundational principles across the uploaded documents.',
      query: 'What are the main topics and core principles explained in the uploaded documents?',
      icon: <FileText size={16} color="var(--accent-cyan)" />,
    },
    {
      title: 'Cross-Domain Comparison',
      desc: 'Find similarities or contrasting approaches across different sections.',
      query: 'Compare the primary concepts and highlight key differences across the topics.',
      icon: <Sparkles size={16} color="var(--accent-purple)" />,
    },
    {
      title: 'Structured Study Summary',
      desc: 'Generate clear, bulleted study takeaways with architectural insights.',
      query: 'Provide a structured summary of the key takeaways and critical mechanisms.',
      icon: <BookOpen size={16} color="var(--accent-emerald)" />,
    },
    {
      title: 'Generate Practice Quiz',
      desc: 'Test your knowledge with challenging multi-part questions.',
      query: 'Create 3 conceptual practice questions based on the document facts to test my understanding.',
      icon: <HelpCircle size={16} color="var(--accent-amber)" />,
    },
  ];

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 64px)',
      backgroundColor: 'var(--bg-primary)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Scrollable Message History Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px 32px',
        display: 'flex',
        flexDirection: 'column',
        gap: '24px',
      }}>
        {/* Empty State / Starter Guide */}
        {messages.length === 0 && (
          <div style={{
            maxWidth: '780px',
            margin: '40px auto',
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '18px',
          }}>
            <div style={{
              width: '64px',
              height: '64px',
              borderRadius: 'var(--radius-xl)',
              background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.2) 0%, rgba(6, 182, 212, 0.2) 100%)',
              border: '1px solid var(--border-glow)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 30px rgba(99, 102, 241, 0.25)',
            }}>
              <Brain size={34} color="var(--accent-cyan)" />
            </div>

            <div>
              <h2 style={{ fontSize: '26px', marginBottom: '8px', fontWeight: 700 }}>
                DocMind Second Brain
              </h2>
              <p style={{ color: 'var(--text-secondary)', fontSize: '15px', maxWidth: '540px', margin: '0 auto' }}>
                Ask questions against your document library. Ground-truth retrieval is enriched with selective memory and cross-document wiki concepts.
              </p>
            </div>

            {/* Starter Prompts Grid */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: '14px',
              width: '100%',
              marginTop: '16px',
            }}>
              {starterPrompts.map((p, i) => (
                <div
                  key={i}
                  onClick={() => onSendMessage(p.query)}
                  className="glass-panel"
                  style={{
                    padding: '16px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                    border: '1px solid var(--border-subtle)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--accent-cyan)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border-subtle)';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                    {p.icon}
                    <span style={{ fontSize: '14px', fontWeight: 600 }}>{p.title}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {p.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Message Bubbles */}
        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          const isContextExpanded = expandedContextIndex === index;
          const meta = msg.metadata;
          const isLastMessage = index === messages.length - 1;
          const isCurrentlyGenerating = isGenerating && isLastMessage && !isUser;
          const hasContent = Boolean(msg.content && msg.content.trim().length > 0);

          return (
            <div
              key={index}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start',
                width: '100%',
              }}
            >
              <div style={{
                display: 'flex',
                gap: '12px',
                maxWidth: isUser ? '75%' : '88%',
                alignItems: 'flex-start',
              }}>
                {/* Assistant Avatar */}
                {!isUser && (
                  <div style={{
                    width: '34px',
                    height: '34px',
                    borderRadius: 'var(--radius-md)',
                    background: 'linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-cyan) 100%)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: '4px',
                    boxShadow: 'var(--shadow-sm)',
                  }}>
                    <Bot size={18} color="#ffffff" />
                  </div>
                )}

                {/* Bubble Container */}
                <div style={{
                  backgroundColor: isUser ? 'var(--bg-tertiary)' : 'var(--bg-card)',
                  border: isUser ? '1px solid var(--border-glow)' : '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '16px 20px',
                  boxShadow: 'var(--shadow-sm)',
                  width: '100%',
                  backdropFilter: isUser ? 'none' : 'blur(10px)',
                  transition: 'border-color var(--transition-fast)',
                }}>
                  {isUser ? (
                    <div style={{ fontSize: '15px', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                      {msg.content}
                    </div>
                  ) : (
                    <div>
                      {/* Thinking State when waiting for first token */}
                      {isCurrentlyGenerating && !hasContent && (
                        <div style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          padding: '4px 0',
                          color: 'var(--accent-primary)',
                          fontSize: '13px',
                        }}>
                          <span className="pulsing-dot online" />
                          <span style={{ fontStyle: 'italic', fontFamily: 'var(--font-body)' }}>
                            DocMind is synthesizing grounded response...
                          </span>
                        </div>
                      )}

                      {/* Markdown Assistant Content with streaming cursor */}
                      {hasContent && (
                        <div className="markdown-body">
                          <ReactMarkdown>{msg.content}</ReactMarkdown>
                          {isCurrentlyGenerating && <span className="streaming-cursor" />}
                        </div>
                      )}

                      {/* Only show Second Brain Context Inspector & Action Buttons when completed (or not currently generating) AND has content */}
                      {!isCurrentlyGenerating && hasContent && (
                        <>
                          {/* Second Brain Injected Context Inspector */}
                          {meta && (meta.retrieved_chunks > 0 || meta.injected_concepts > 0 || meta.injected_memories > 0) && (
                            <div style={{
                              marginTop: '14px',
                              paddingTop: '12px',
                              borderTop: '1px solid var(--border-subtle)',
                            }}>
                              <button
                                onClick={() => setExpandedContextIndex(isContextExpanded ? null : index)}
                                style={{
                                  background: 'transparent',
                                  border: 'none',
                                  color: 'var(--text-secondary)',
                                  fontSize: '12px',
                                  cursor: 'pointer',
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: '6px',
                                  padding: 0,
                                }}
                              >
                                <Brain size={14} color="var(--accent-cyan)" />
                                <span>Second Brain Context Utilized:</span>
                                <span className="badge badge-cyan" style={{ fontSize: '10px' }}>
                                  {meta.retrieved_chunks || 0} Chunks
                                </span>
                                {meta.injected_concepts > 0 && (
                                  <span className="badge badge-purple" style={{ fontSize: '10px' }}>
                                    {meta.injected_concepts} Wiki Concepts
                                  </span>
                                )}
                                {meta.injected_memories > 0 && (
                                  <span className="badge badge-emerald" style={{ fontSize: '10px' }}>
                                    {meta.injected_memories} Memories
                                  </span>
                                )}
                                {isContextExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                              </button>

                              {/* Expanded Context Details */}
                              {isContextExpanded && (
                                <div style={{
                                  marginTop: '10px',
                                  padding: '12px',
                                  borderRadius: 'var(--radius-md)',
                                  background: 'rgba(0, 0, 0, 0.25)',
                                  fontSize: '12px',
                                  display: 'flex',
                                  flexDirection: 'column',
                                  gap: '8px',
                                }}>
                                  {meta.sources && meta.sources.length > 0 && (
                                    <div>
                                      <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, marginBottom: '4px' }}>
                                        Ground-Truth Document Sources:
                                      </div>
                                      <ul style={{ paddingLeft: '16px', margin: 0, color: 'var(--text-secondary)' }}>
                                        {meta.sources.map((s, si) => (
                                          <li key={si}>
                                            {s.document_id || s.filename || 'PDF'} (Page {s.page || 1})
                                          </li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                  {meta.wiki_concepts && meta.wiki_concepts.length > 0 && (
                                    <div>
                                      <div style={{ color: 'var(--accent-purple)', fontWeight: 600, marginBottom: '4px' }}>
                                        Injected Wiki Concepts:
                                      </div>
                                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                                        {meta.wiki_concepts.map((c, ci) => (
                                          <span key={ci} className="badge badge-purple">
                                            🌐 {c}
                                          </span>
                                        ))}
                                      </div>
                                    </div>
                                  )}
                                </div>
                              )}
                            </div>
                          )}

                          {/* Response Action Bar */}
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'flex-end',
                            gap: '8px',
                            marginTop: '12px',
                          }}>
                            <button
                              onClick={() => handleCopy(msg.content, index)}
                              className="btn-ghost btn-sm"
                              style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
                              title="Copy Answer"
                            >
                              {copiedIndex === index ? <Check size={12} color="var(--accent-emerald)" /> : <Copy size={12} />}
                              <span>{copiedIndex === index ? 'Copied' : 'Copy'}</span>
                            </button>

                            <button
                              onClick={() => onSaveToMemory(msg.content)}
                              className="btn-ghost btn-sm"
                              style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--accent-purple)' }}
                              title="Save key insight to Second Brain Selective Memory"
                            >
                              <BookmarkPlus size={12} />
                              <span>Save to Memory</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* User Avatar */}
                {isUser && (
                  <div style={{
                    width: '34px',
                    height: '34px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    marginTop: '4px',
                  }}>
                    <User size={18} color="var(--text-secondary)" />
                  </div>
                )}
              </div>
            </div>
          );
        })}

        <div ref={messagesEndRef} />
      </div>

      {/* Floating Bottom Input Area */}
      <div style={{
        padding: '16px 32px 24px',
        backgroundColor: 'var(--bg-glass)',
        backdropFilter: 'blur(12px)',
        borderTop: '1px solid var(--border-subtle)',
      }}>
        <div style={{
          maxWidth: '840px',
          margin: '0 auto',
          position: 'relative',
        }}>
          {/* Scope Indicator Chip */}
          <div style={{
            position: 'absolute',
            top: '-28px',
            left: '4px',
            fontSize: '11px',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}>
            <Layers size={12} color="var(--accent-cyan)" />
            <span>Targeting: <strong style={{ color: 'var(--text-secondary)' }}>{selectedFolder}</strong></span>
          </div>

          {/* Text Input Container */}
          <form
            onSubmit={handleSubmit}
            style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--bg-glass-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-xl)',
              padding: '6px 12px 6px 18px',
              boxShadow: 'var(--shadow-md)',
              transition: 'border-color var(--transition-fast)',
            }}
          >
            <textarea
              ref={textareaRef}
              rows={1}
              value={inputQuery}
              onChange={(e) => {
                setInputQuery(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
              }}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your documents, compare concepts, or request study notes..."
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-body)',
                fontSize: '14px',
                lineHeight: '1.5',
                outline: 'none',
                resize: 'none',
                maxHeight: '120px',
                padding: '8px 0',
              }}
            />

            <button
              type="submit"
              disabled={!inputQuery.trim() || isGenerating}
              className="btn btn-primary btn-icon"
              style={{
                opacity: !inputQuery.trim() || isGenerating ? 0.4 : 1,
                cursor: !inputQuery.trim() || isGenerating ? 'not-allowed' : 'pointer',
                flexShrink: 0,
              }}
              title="Send (Enter)"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
