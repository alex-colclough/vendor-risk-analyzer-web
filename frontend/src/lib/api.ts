const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Request failed' }));
      return { error: error.detail || error.error || 'Request failed' };
    }

    const data = await response.json();
    return { data };
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Network error' };
  }
}

export const api = {
  // File Upload
  async uploadFile(sessionId: string, file: File) {
    const formData = new FormData();
    formData.append('session_id', sessionId);
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE}/api/v1/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Upload failed' }));
        return { error: error.detail || error.error || 'Upload failed' };
      }

      return await response.json();
    } catch (err) {
      return { error: err instanceof Error ? err.message : 'Upload failed' };
    }
  },

  async getFiles(sessionId: string) {
    return fetchApi<{
      session_id: string;
      files: Array<{
        id: string;
        original_name: string;
        size_bytes: number;
        mime_type: string;
        uploaded_at: string;
      }>;
      total_size_bytes: number;
    }>(`/api/v1/upload/${sessionId}`);
  },

  async deleteFile(sessionId: string, fileId: string) {
    return fetchApi(`/api/v1/upload/${sessionId}/${fileId}`, {
      method: 'DELETE',
    });
  },

  // Analysis
  async startAnalysis(sessionId: string, frameworks: string[]) {
    return fetchApi<{
      analysis_id: string;
      session_id: string;
      status: string;
      message: string;
    }>('/api/v1/analysis/start', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, frameworks }),
    });
  },

  async getAnalysisStatus(analysisId: string) {
    return fetchApi<{
      analysis_id: string;
      status: string;
      progress_percentage: number;
      current_step?: string;
      error?: string;
    }>(`/api/v1/analysis/${analysisId}/status`);
  },

  async getAnalysisResults(analysisId: string) {
    return fetchApi(`/api/v1/analysis/${analysisId}/results`);
  },

  // Connection Test
  async testConnection(region?: string, modelId?: string) {
    return fetchApi<{
      success: boolean;
      region: string;
      model_id: string;
      message: string;
      latency_ms?: number;
      error?: string;
    }>('/api/v1/connection/test', {
      method: 'POST',
      body: JSON.stringify({ region, model_id: modelId }),
    });
  },

  // Chat
  async sendChatMessage(sessionId: string, message: string) {
    return fetchApi<{
      message_id: string;
      role: string;
      content: string;
      timestamp: string;
    }>('/api/v1/chat', {
      method: 'POST',
      body: JSON.stringify({
        session_id: sessionId,
        message,
        include_context: true,
      }),
    });
  },

  // Export
  getExportJsonUrl(analysisId: string) {
    return `${API_BASE}/api/v1/export/json/${analysisId}`;
  },

  getExportPdfUrl(analysisId: string) {
    return `${API_BASE}/api/v1/export/pdf/${analysisId}`;
  },
};
