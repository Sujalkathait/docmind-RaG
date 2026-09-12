/**
 * DocMind Second Brain API Client
 * Connects React frontend directly to local FastAPI server on port 8000.
 * 100% offline, zero external API keys, runs locally.
 */

const API_BASE = '';

export const api = {
  // System Health & Local Model Telemetry
  async getHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (!res.ok) throw new Error('Health check failed');
      return await res.json();
    } catch (err) {
      return { status: 'offline', active_model: 'Unavailable', llm_ready: false, gpu_layers: 0, available_models: [] };
    }
  },

  async getModels() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/models`);
      if (!res.ok) return { available_models: [] };
      return await res.json();
    } catch (err) {
      return { available_models: [] };
    }
  },

  async switchModel(modelName) {
    const res = await fetch(`${API_BASE}/api/v1/models/switch`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Model switch failed');
    }
    return await res.json();
  },

  // Document Management
  async getDocuments(folder = null, limit = 50, offset = 0) {
    let url = `${API_BASE}/api/v1/documents?limit=${limit}&offset=${offset}`;
    if (folder && folder !== 'All Collections' && folder !== 'All') {
      url += `&folder=${encodeURIComponent(folder)}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch documents');
    const data = await res.json();
    return Array.isArray(data) ? { documents: data } : data;
  },

  async uploadDocument(file, folder = 'General') {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('folder', folder);

    const res = await fetch(`${API_BASE}/api/v1/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Upload failed');
    }
    return await res.json();
  },

  async deleteDocument(docId) {
    const res = await fetch(`${API_BASE}/api/v1/documents/${encodeURIComponent(docId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete document');
    return await res.json();
  },

  async getFolders() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents/folders`);
      if (!res.ok) return ['General'];
      const data = await res.json();
      return data.folders || ['General'];
    } catch (e) {
      return ['General'];
    }
  },

  // Knowledge & Wiki Concepts
  async getWikiGraph() {
    const res = await fetch(`${API_BASE}/api/v1/knowledge/graph`);
    if (!res.ok) throw new Error('Failed to fetch knowledge graph');
    return await res.json();
  },

  async getWikiConcepts() {
    const res = await fetch(`${API_BASE}/api/v1/knowledge/concepts`);
    if (!res.ok) throw new Error('Failed to fetch concepts');
    const data = await res.json();
    return Array.isArray(data) ? { concepts: data } : data;
  },

  async mineConcepts(docId) {
    const res = await fetch(`${API_BASE}/api/v1/knowledge/mine/${encodeURIComponent(docId)}`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Concept mining failed');
    }
    return await res.json();
  },

  // Selective Memory Operations
  async getMemories(userId = 'default_user', category = null, limit = 50) {
    let url = `${API_BASE}/api/v1/memory?user_id=${encodeURIComponent(userId)}&limit=${limit}`;
    if (category && category !== 'all') {
      url += `&category=${encodeURIComponent(category)}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch memories');
    const data = await res.json();
    return Array.isArray(data) ? { memories: data } : data;
  },

  async addMemory(userId = 'default_user', category, content, importanceScore = 0.5, metadata = {}) {
    const res = await fetch(`${API_BASE}/api/v1/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        category,
        content,
        value: content,
        importance_score: importanceScore,
        metadata,
      }),
    });
    if (!res.ok) throw new Error('Failed to save memory');
    return await res.json();
  },

  async deleteMemory(memoryId) {
    const res = await fetch(`${API_BASE}/api/v1/memory/${encodeURIComponent(memoryId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error('Failed to delete memory');
    return await res.json();
  },

  // Study Outputs & Deliverables
  async generateOutput(deliverableType, docId = null, folder = null, title = null, notes = null) {
    const topic = title || (folder && folder !== 'All Collections' ? `${folder} Study Notes` : 'Core Concepts');
    const res = await fetch(`${API_BASE}/api/v1/outputs/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        title,
        deliverable_type: deliverableType,
        doc_id: docId,
        folder_scope: (folder && folder !== 'All Collections') ? [folder] : null,
        notes,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Generation failed');
    }
    return await res.json();
  },

  async getOutputs(deliverableType = null, limit = 20) {
    let url = `${API_BASE}/api/v1/outputs?limit=${limit}`;
    if (deliverableType && deliverableType !== 'all') {
      url += `&output_type=${encodeURIComponent(deliverableType.toUpperCase())}`;
    }
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch deliverables');
    const data = await res.json();
    return Array.isArray(data) ? { outputs: data } : data;
  },

  // Chat Sessions & History
  async getSessions() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/sessions`);
      if (!res.ok) return { sessions: [] };
      const data = await res.json();
      return Array.isArray(data) ? { sessions: data } : data;
    } catch (e) {
      return { sessions: [] };
    }
  },

  async getChatHistory(sessionId) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/history/${encodeURIComponent(sessionId)}`);
      if (!res.ok) return [];
      return await res.json();
    } catch (e) {
      return [];
    }
  },

  async deleteSession(sessionId) {
    const res = await fetch(`${API_BASE}/api/v1/chat/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to delete chat session');
    }
    return await res.json();
  },

  // Streaming Chat with Context Breakdown
  async streamChat({ query, folder, sessionId, userId = 'default_user', onChunk, onDone, onError }) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: query,
          query,
          folder_scope: (folder && folder !== 'All Collections') ? [folder] : null,
          folder: (folder && folder !== 'All Collections') ? folder : null,
          conversation_id: sessionId,
          session_id: sessionId,
          user_id: userId,
          stream: true,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server error: ${res.status}`);
      }

      const contentType = res.headers.get('content-type') || '';

      if (contentType.includes('text/event-stream')) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';
        let fullText = '';
        let metadata = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop(); // Keep uncompleted line

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data:')) {
              const payloadStr = trimmed.slice(5).trim();
              if (payloadStr === '[DONE]') continue;
              try {
                const payload = JSON.parse(payloadStr);
                if (payload.delta) {
                  fullText += payload.delta;
                  if (onChunk) onChunk(payload.delta, fullText);
                }
                if (payload.metadata) {
                  metadata = payload.metadata;
                }
              } catch (e) {
                fullText += payloadStr;
                if (onChunk) onChunk(payloadStr, fullText);
              }
            }
          }
        }
        if (onDone) onDone(fullText, metadata);
      } else {
        const data = await res.json();
        if (onDone) onDone(data.answer, data.metadata || data);
      }
    } catch (err) {
      if (onError) onError(err);
      else console.error('Chat error:', err);
    }
  },
};
