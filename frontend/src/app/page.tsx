'use client';

import { RefreshCw } from 'lucide-react';
import Image from 'next/image';
import { Button } from '@/components/ui/button';
import { FileDropzone } from '@/components/FileDropzone';
import { FrameworkSelector } from '@/components/FrameworkSelector';
import { AnalysisPanel } from '@/components/AnalysisPanel';
import { ResultsDashboard } from '@/components/ResultsDashboard';
import { ChatWindow } from '@/components/ChatWindow';
import { ConnectionTest } from '@/components/ConnectionTest';
import { ThemeToggle } from '@/components/ThemeToggle';
import { useStore } from '@/store';

export default function Home() {
  const { sessionId, reset, analysisStatus } = useStore();

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b sticky top-0 bg-background/95 backdrop-blur z-40">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Image
              src="/logo.jpg"
              alt="Logo"
              width={120}
              height={40}
              className="h-10 w-auto object-contain"
            />
            <div>
              <h1 className="text-xl font-bold">Vendor Security Analyzer</h1>
              <p className="text-xs text-muted-foreground">
                AI-Powered Compliance Analysis
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <ConnectionTest />
            <Button
              variant="outline"
              size="sm"
              onClick={reset}
              className="gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              New Analysis
            </Button>
            <ThemeToggle />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid gap-6">
          {/* Upload and Configuration */}
          {analysisStatus !== 'completed' && (
            <>
              <div className="grid md:grid-cols-2 gap-6">
                <FileDropzone />
                <FrameworkSelector />
              </div>
              <AnalysisPanel />
            </>
          )}

          {/* Results */}
          <ResultsDashboard />
        </div>

        {/* Session Info (debug) */}
        <div className="mt-8 text-center text-xs text-muted-foreground">
          Session: {sessionId}
        </div>
      </main>

      {/* Chat Window */}
      <ChatWindow />
    </div>
  );
}
