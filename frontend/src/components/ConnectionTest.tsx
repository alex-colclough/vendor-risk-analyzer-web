'use client';

import { useState } from 'react';
import { Wifi, WifiOff, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { api } from '@/lib/api';
import type { ConnectionStatus } from '@/types';

export function ConnectionTest() {
  const [isOpen, setIsOpen] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [result, setResult] = useState<ConnectionStatus | null>(null);

  const handleTest = async () => {
    setIsTesting(true);
    setResult(null);

    try {
      const response = await api.testConnection();
      if (response.data) {
        setResult(response.data);
      } else {
        setResult({
          success: false,
          region: '',
          model_id: '',
          message: 'Connection test failed',
          error: response.error,
        });
      }
    } catch (err) {
      setResult({
        success: false,
        region: '',
        model_id: '',
        message: 'Connection test failed',
        error: err instanceof Error ? err.message : 'Unknown error',
      });
    }

    setIsTesting(false);
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Wifi className="h-4 w-4" />
          Test Connection
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>AWS Bedrock Connection Test</DialogTitle>
          <DialogDescription>
            Test the connection to AWS Bedrock to verify credentials and model access.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <Button
            onClick={handleTest}
            disabled={isTesting}
            className="w-full gap-2"
          >
            {isTesting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Testing...
              </>
            ) : (
              <>
                <Wifi className="h-4 w-4" />
                Run Connection Test
              </>
            )}
          </Button>

          {result && (
            <div
              className={`p-4 rounded-lg ${
                result.success
                  ? 'bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800'
                  : 'bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800'
              }`}
            >
              <div className="flex items-center gap-2 mb-2">
                {result.success ? (
                  <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
                )}
                <span
                  className={`font-medium ${
                    result.success
                      ? 'text-green-700 dark:text-green-300'
                      : 'text-red-700 dark:text-red-300'
                  }`}
                >
                  {result.success ? 'Connection Successful' : 'Connection Failed'}
                </span>
              </div>

              <p className="text-sm text-muted-foreground mb-2">
                {result.message}
              </p>

              {result.success && (
                <div className="space-y-1 text-sm">
                  <p>
                    <span className="font-medium">Region:</span> {result.region}
                  </p>
                  <p>
                    <span className="font-medium">Model:</span> {result.model_id}
                  </p>
                  {result.latency_ms && (
                    <p>
                      <span className="font-medium">Latency:</span>{' '}
                      {result.latency_ms.toFixed(0)}ms
                    </p>
                  )}
                </div>
              )}

              {result.error && (
                <p className="text-sm text-red-600 dark:text-red-400 mt-2">
                  {result.error}
                </p>
              )}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
