import React, { useState, useMemo, useRef } from 'react';
import {
  Network,
  Share2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Sparkles,
  Info,
  ExternalLink,
  ArrowRight,
  BookOpen,
} from 'lucide-react';

export default function WikiGraphVisualizer({
  nodes = [],
  edges = [],
  selectedConcept,
  onSelectConcept,
  onMineClick,
  isMining,
}) {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredNodeId, setHoveredNodeId] = useState(null);

  const containerRef = useRef(null);
  const width = 860;
  const height = 480;

  // Compute 2D node positions in a circular / orbital cluster layout
  const layoutNodes = useMemo(() => {
    if (!nodes || nodes.length === 0) return [];

    const total = nodes.length;
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = Math.min(width, height) * 0.38;

    return nodes.map((node, i) => {
      // Golden angle distribution for pleasant organic layout
      const angle = (i * 2.39996323) % (2 * Math.PI);
      // Distance distributes outwards if many nodes
      const r = total > 8 ? radius * (0.45 + 0.55 * (i / total)) : radius * 0.75;
      const x = centerX + r * Math.cos(angle);
      const y = centerY + r * Math.sin(angle);

      return {
        ...node,
        x,
        y,
      };
    });
  }, [nodes]);

  // Lookup map for fast edge coordinate calculation
  const nodePositionMap = useMemo(() => {
    const map = new Map();
    layoutNodes.forEach((n) => {
      map.set(n.name?.toLowerCase(), { x: n.x, y: n.y, node: n });
      map.set(n.id, { x: n.x, y: n.y, node: n });
    });
    return map;
  }, [layoutNodes]);

  // Build resolved edges with coordinates
  const resolvedEdges = useMemo(() => {
    if (!edges || edges.length === 0) return [];

    return edges
      .map((edge) => {
        const srcPos = nodePositionMap.get(edge.source?.toLowerCase());
        const tgtPos = nodePositionMap.get(edge.target?.toLowerCase());

        if (srcPos && tgtPos) {
          return {
            ...edge,
            x1: srcPos.x,
            y1: srcPos.y,
            x2: tgtPos.x,
            y2: tgtPos.y,
            sourceNode: srcPos.node,
            targetNode: tgtPos.node,
          };
        }
        return null;
      })
      .filter(Boolean);
  }, [edges, nodePositionMap]);

  // Connected neighbors for active selection
  const connectedNeighbors = useMemo(() => {
    if (!selectedConcept) return new Set();
    const set = new Set();
    const name = selectedConcept.name?.toLowerCase();

    resolvedEdges.forEach((e) => {
      if (e.source?.toLowerCase() === name) {
        set.add(e.target?.toLowerCase());
      } else if (e.target?.toLowerCase() === name) {
        set.add(e.source?.toLowerCase());
      }
    });
    return set;
  }, [selectedConcept, resolvedEdges]);

  // Mouse pan handlers
  const handleMouseDown = (e) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  if (nodes.length === 0) {
    return (
      <div
        style={{
          background: 'rgba(255, 255, 255, 0.02)',
          border: '1px dashed var(--border-glow)',
          borderRadius: 'var(--radius-lg)',
          padding: '48px 24px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
        }}
      >
        <Network size={36} color="var(--accent-cyan)" />
        <h4 style={{ fontSize: '16px', fontWeight: 600 }}>Wiki Knowledge Graph is Empty</h4>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '460px', margin: 0 }}>
          Upload PDFs into your Vault, then extract structured concepts and cross-document semantic relationships to build your interactive knowledge graph.
        </p>
        {onMineClick && (
          <button
            onClick={onMineClick}
            disabled={isMining}
            className="btn btn-primary"
            style={{ marginTop: '8px' }}
          >
            <Sparkles size={15} />
            <span>{isMining ? 'Mining Concepts...' : 'Extract Concepts from PDFs'}</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* Visual Canvas Container */}
      <div
        ref={containerRef}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        style={{
          width: '100%',
          height: `${height}px`,
          backgroundColor: '#0c0e17',
          backgroundImage: 'radial-gradient(rgba(99, 102, 241, 0.12) 1px, transparent 1px)',
          backgroundSize: '24px 24px',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border-subtle)',
          position: 'relative',
          overflow: 'hidden',
          cursor: isDragging ? 'grabbing' : 'grab',
          userSelect: 'none',
        }}
      >
        {/* Floating Zoom & Control Bar */}
        <div
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(15, 23, 42, 0.75)',
            backdropFilter: 'blur(8px)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-md)',
            padding: '4px 6px',
            zIndex: 10,
          }}
        >
          <button
            onClick={() => setZoom((z) => Math.min(2.5, z + 0.2))}
            className="btn-ghost"
            style={{ padding: '4px', border: 'none', cursor: 'pointer' }}
            title="Zoom In"
          >
            <ZoomIn size={14} color="var(--text-secondary)" />
          </button>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', minWidth: '34px', textAlign: 'center' }}>
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.max(0.5, z - 0.2))}
            className="btn-ghost"
            style={{ padding: '4px', border: 'none', cursor: 'pointer' }}
            title="Zoom Out"
          >
            <ZoomOut size={14} color="var(--text-secondary)" />
          </button>
          <button
            onClick={handleResetView}
            className="btn-ghost"
            style={{ padding: '4px', border: 'none', cursor: 'pointer' }}
            title="Reset View"
          >
            <Maximize2 size={14} color="var(--text-secondary)" />
          </button>
        </div>

        {/* Legend / Overlay Info */}
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            fontSize: '11px',
            color: 'var(--text-muted)',
            background: 'rgba(15, 23, 42, 0.7)',
            padding: '4px 10px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            pointerEvents: 'none',
            display: 'flex',
            gap: '12px',
          }}
        >
          <span>✨ Click node to inspect</span>
          <span>• Drag to pan</span>
          <span>• {nodes.length} Concepts, {resolvedEdges.length} Links</span>
        </div>

        {/* Interactive SVG Network */}
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${width} ${height}`}
          style={{ overflow: 'visible' }}
        >
          <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
            {/* Defs for arrowheads and glow filters */}
            <defs>
              <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="var(--accent-primary, #6366f1)" stopOpacity="0.6" />
                <stop offset="100%" stopColor="var(--accent-cyan, #06b6d4)" stopOpacity="0.6" />
              </linearGradient>

              <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feComposite in="SourceGraphic" in2="blur" operator="over" />
              </filter>
            </defs>

            {/* EDGES / RELATIONSHIP LINES */}
            {resolvedEdges.map((edge, idx) => {
              const isSelectedEdge =
                selectedConcept &&
                (edge.source?.toLowerCase() === selectedConcept.name?.toLowerCase() ||
                  edge.target?.toLowerCase() === selectedConcept.name?.toLowerCase());

              const isDimmed = selectedConcept && !isSelectedEdge;

              const midX = (edge.x1 + edge.x2) / 2;
              const midY = (edge.y1 + edge.y2) / 2;

              return (
                <g key={idx} style={{ transition: 'opacity 0.2s ease', opacity: isDimmed ? 0.2 : 0.85 }}>
                  <line
                    x1={edge.x1}
                    y1={edge.y1}
                    x2={edge.x2}
                    y2={edge.y2}
                    stroke={isSelectedEdge ? 'var(--accent-cyan)' : 'url(#edgeGradient)'}
                    strokeWidth={isSelectedEdge ? 2.5 : 1.5}
                    strokeDasharray={edge.relation_type === 'similar_to' ? '4 2' : undefined}
                  />

                  {/* Relationship Label Pill */}
                  <rect
                    x={midX - 32}
                    y={midY - 8}
                    width="64"
                    height="16"
                    rx="4"
                    fill="rgba(10, 15, 30, 0.85)"
                    stroke={isSelectedEdge ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.1)'}
                    strokeWidth="0.8"
                  />
                  <text
                    x={midX}
                    y={midY + 3.5}
                    textAnchor="middle"
                    fill={isSelectedEdge ? 'var(--accent-cyan)' : 'var(--text-muted)'}
                    fontSize="8.5"
                    fontFamily="inherit"
                    fontWeight="500"
                  >
                    {edge.relation_type || 'related_to'}
                  </text>
                </g>
              );
            })}

            {/* CONCEPT NODES */}
            {layoutNodes.map((node) => {
              const isSelected = selectedConcept?.id === node.id;
              const isNeighbor = connectedNeighbors.has(node.name?.toLowerCase());
              const isHovered = hoveredNodeId === node.id;
              const isDimmed = selectedConcept && !isSelected && !isNeighbor;

              return (
                <g
                  key={node.id}
                  transform={`translate(${node.x}, ${node.y})`}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (onSelectConcept) onSelectConcept(node);
                  }}
                  onMouseEnter={() => setHoveredNodeId(node.id)}
                  onMouseLeave={() => setHoveredNodeId(null)}
                  style={{
                    cursor: 'pointer',
                    transition: 'opacity 0.25s ease, transform 0.2s ease',
                    opacity: isDimmed ? 0.35 : 1,
                  }}
                >
                  {/* Outer Pulsing Aura for Selected Node */}
                  {isSelected && (
                    <circle
                      r="28"
                      fill="none"
                      stroke="var(--accent-cyan)"
                      strokeWidth="1.5"
                      strokeDasharray="4 2"
                      opacity="0.8"
                    >
                      <animateTransform
                        attributeName="transform"
                        type="rotate"
                        from="0"
                        to="360"
                        dur="10s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  )}

                  {/* Main Node Circle */}
                  <circle
                    r={isSelected ? 18 : isNeighbor ? 16 : 14}
                    fill={
                      isSelected
                        ? 'var(--accent-cyan)'
                        : isNeighbor
                        ? 'var(--accent-purple)'
                        : '#1e293b'
                    }
                    stroke={
                      isSelected
                        ? '#ffffff'
                        : isHovered
                        ? 'var(--accent-cyan)'
                        : 'rgba(255, 255, 255, 0.2)'
                    }
                    strokeWidth={isSelected ? 2.5 : 1.5}
                    filter={isSelected || isHovered ? 'url(#glow)' : undefined}
                  />

                  {/* Central Node Icon or Initial */}
                  <text
                    textAnchor="middle"
                    dy=".3em"
                    fill={isSelected ? '#000000' : '#ffffff'}
                    fontSize={isSelected ? '11' : '10'}
                    fontWeight="700"
                    fontFamily="inherit"
                  >
                    {node.name ? node.name.charAt(0).toUpperCase() : '•'}
                  </text>

                  {/* Node Label Text */}
                  <text
                    y={isSelected ? 30 : 26}
                    textAnchor="middle"
                    fill={
                      isSelected
                        ? 'var(--accent-cyan)'
                        : isNeighbor
                        ? '#e2e8f0'
                        : 'var(--text-secondary)'
                    }
                    fontSize={isSelected ? '12' : '10.5'}
                    fontWeight={isSelected ? '700' : '500'}
                    fontFamily="inherit"
                    style={{
                      textShadow: '0 2px 4px rgba(0,0,0,0.8)',
                    }}
                  >
                    {node.name}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* SELECTED CONCEPT INSPECTOR DRAWER */}
      {selectedConcept && (
        <div
          className="glass-panel"
          style={{
            padding: '16px 20px',
            border: '1px solid var(--border-glow)',
            borderRadius: 'var(--radius-md)',
            background: 'linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(15, 23, 42, 0.8) 100%)',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            animation: 'fadeIn 0.2s ease',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '18px' }}>🌐</span>
              <h4 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>
                {selectedConcept.name}
              </h4>
              <span className="badge badge-purple" style={{ fontSize: '10px' }}>
                {selectedConcept.category || 'CONCEPT'}
              </span>
            </div>

            <button
              onClick={() => onSelectConcept(null)}
              className="btn-ghost"
              style={{ fontSize: '12px', color: 'var(--text-muted)', padding: '2px 6px' }}
            >
              ✕ Close
            </button>
          </div>

          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {selectedConcept.definition || selectedConcept.summary || 'Extracted concept from uploaded documents.'}
          </div>

          {/* Connected Neighbor Badges */}
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Direct Cross-Document Relationships ({connectedNeighbors.size})
            </div>
            {connectedNeighbors.size === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                No direct edges linked yet. Click 'Extract Concepts' to auto-discover relationships.
              </div>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                {Array.from(connectedNeighbors).map((name) => {
                  const targetNode = nodes.find((n) => n.name?.toLowerCase() === name);
                  return (
                    <button
                      key={name}
                      onClick={() => targetNode && onSelectConcept(targetNode)}
                      className="btn btn-secondary btn-sm"
                      style={{
                        fontSize: '11px',
                        padding: '3px 8px',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '4px',
                        border: '1px solid var(--border-subtle)',
                      }}
                      title={`Jump to ${name}`}
                    >
                      <ArrowRight size={11} color="var(--accent-cyan)" />
                      <span>{targetNode ? targetNode.name : name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
