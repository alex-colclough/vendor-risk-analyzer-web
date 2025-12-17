import { create } from 'zustand';
import type {
  UploadedFile,
  AnalysisResults,
  ChatMessage,
  ProgressEvent,
  AnalysisStatus,
} from '@/types';
import { generateSessionId } from '@/lib/utils';

interface AppState {
  // Session
  sessionId: string;

  // Upload state
  uploadedFiles: UploadedFile[];
  isUploading: boolean;

  // Framework selection
  selectedFrameworks: string[];

  // Analysis state
  analysisId: string | null;
  analysisStatus: AnalysisStatus;
  progress: number;
  progressMessages: ProgressEvent[];

  // Results
  results: AnalysisResults | null;

  // Chat
  chatMessages: ChatMessage[];
  isChatOpen: boolean;

  // Connection
  isConnected: boolean;

  // Actions
  setSessionId: (id: string) => void;
  addFile: (file: UploadedFile) => void;
  removeFile: (fileId: string) => void;
  setFiles: (files: UploadedFile[]) => void;
  setIsUploading: (uploading: boolean) => void;
  toggleFramework: (framework: string) => void;
  setSelectedFrameworks: (frameworks: string[]) => void;
  setAnalysisId: (id: string | null) => void;
  setAnalysisStatus: (status: AnalysisStatus) => void;
  setProgress: (progress: number) => void;
  addProgressMessage: (message: ProgressEvent) => void;
  clearProgressMessages: () => void;
  setResults: (results: AnalysisResults | null) => void;
  addChatMessage: (message: ChatMessage) => void;
  setChatMessages: (messages: ChatMessage[]) => void;
  toggleChat: () => void;
  setIsConnected: (connected: boolean) => void;
  reset: () => void;
}

const initialState = {
  sessionId: generateSessionId(),
  uploadedFiles: [],
  isUploading: false,
  selectedFrameworks: ['SOC2', 'ISO27001', 'NIST_CSF'],
  analysisId: null,
  analysisStatus: 'idle' as AnalysisStatus,
  progress: 0,
  progressMessages: [],
  results: null,
  chatMessages: [],
  isChatOpen: false,
  isConnected: false,
};

export const useStore = create<AppState>((set) => ({
  ...initialState,

  setSessionId: (id) => set({ sessionId: id }),

  addFile: (file) =>
    set((state) => ({
      uploadedFiles: [...state.uploadedFiles, file],
    })),

  removeFile: (fileId) =>
    set((state) => ({
      uploadedFiles: state.uploadedFiles.filter((f) => f.id !== fileId),
    })),

  setFiles: (files) => set({ uploadedFiles: files }),

  setIsUploading: (uploading) => set({ isUploading: uploading }),

  toggleFramework: (framework) =>
    set((state) => ({
      selectedFrameworks: state.selectedFrameworks.includes(framework)
        ? state.selectedFrameworks.filter((f) => f !== framework)
        : [...state.selectedFrameworks, framework],
    })),

  setSelectedFrameworks: (frameworks) => set({ selectedFrameworks: frameworks }),

  setAnalysisId: (id) => set({ analysisId: id }),

  setAnalysisStatus: (status) => set({ analysisStatus: status }),

  setProgress: (progress) => set({ progress }),

  addProgressMessage: (message) =>
    set((state) => ({
      progressMessages: [...state.progressMessages, message],
    })),

  clearProgressMessages: () => set({ progressMessages: [] }),

  setResults: (results) => set({ results }),

  addChatMessage: (message) =>
    set((state) => ({
      chatMessages: [...state.chatMessages, message],
    })),

  setChatMessages: (messages) => set({ chatMessages: messages }),

  toggleChat: () => set((state) => ({ isChatOpen: !state.isChatOpen })),

  setIsConnected: (connected) => set({ isConnected: connected }),

  reset: () =>
    set({
      ...initialState,
      sessionId: generateSessionId(),
    }),
}));
