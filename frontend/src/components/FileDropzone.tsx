'use client';

import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, File, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { useStore } from '@/store';
import { api } from '@/lib/api';
import { formatBytes } from '@/lib/utils';
import { toast } from '@/hooks/use-toast';

const ACCEPTED_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'application/vnd.ms-excel': ['.xls'],
  'text/csv': ['.csv'],
  'text/plain': ['.txt'],
  'text/markdown': ['.md'],
};

const MAX_SIZE = 100 * 1024 * 1024; // 100MB

export function FileDropzone() {
  const {
    sessionId,
    uploadedFiles,
    isUploading,
    addFile,
    removeFile,
    setIsUploading,
  } = useStore();

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      setIsUploading(true);

      for (const file of acceptedFiles) {
        try {
          const result = await api.uploadFile(sessionId, file);

          if (result.error) {
            toast({
              title: 'Upload failed',
              description: result.error,
              variant: 'destructive',
            });
          } else if (result.success && result.file) {
            addFile(result.file);
            toast({
              title: 'File uploaded',
              description: `${file.name} uploaded successfully`,
            });
          }
        } catch (err) {
          toast({
            title: 'Upload failed',
            description: `Failed to upload ${file.name}`,
            variant: 'destructive',
          });
        }
      }

      setIsUploading(false);
    },
    [sessionId, addFile, setIsUploading]
  );

  const handleRemoveFile = async (fileId: string) => {
    try {
      await api.deleteFile(sessionId, fileId);
      removeFile(fileId);
      toast({
        title: 'File removed',
        description: 'File has been removed',
      });
    } catch {
      toast({
        title: 'Error',
        description: 'Failed to remove file',
        variant: 'destructive',
      });
    }
  };

  const { getRootProps, getInputProps, isDragActive, fileRejections } =
    useDropzone({
      onDrop,
      accept: ACCEPTED_TYPES,
      maxSize: MAX_SIZE,
      disabled: isUploading,
    });

  const totalSize = uploadedFiles.reduce((acc, f) => acc + f.size_bytes, 0);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Upload Documents
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div
          {...getRootProps()}
          className={`
            border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
            transition-colors duration-200
            ${isDragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'}
            ${isUploading ? 'opacity-50 cursor-not-allowed' : 'hover:border-primary/50'}
          `}
        >
          <input {...getInputProps()} />
          <Upload className="h-10 w-10 mx-auto mb-4 text-muted-foreground" />
          {isDragActive ? (
            <p className="text-primary font-medium">Drop files here...</p>
          ) : (
            <>
              <p className="font-medium">
                Drag & drop files here, or click to select
              </p>
              <p className="text-sm text-muted-foreground mt-2">
                Supported: PDF, DOCX, XLSX, XLS, CSV, TXT, MD (max 100MB each)
              </p>
            </>
          )}
        </div>

        {fileRejections.length > 0 && (
          <div className="flex items-center gap-2 text-destructive text-sm">
            <AlertCircle className="h-4 w-4" />
            <span>
              {fileRejections.length} file(s) rejected - check format and size
            </span>
          </div>
        )}

        {isUploading && (
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">Uploading...</p>
            <Progress value={undefined} className="animate-pulse" />
          </div>
        )}

        {uploadedFiles.length > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <p className="text-sm font-medium">
                {uploadedFiles.length} file(s) uploaded
              </p>
              <p className="text-sm text-muted-foreground">
                Total: {formatBytes(totalSize)}
              </p>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {uploadedFiles.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center justify-between p-3 bg-muted rounded-lg"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <File className="h-4 w-4 flex-shrink-0 text-muted-foreground" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">
                        {file.original_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatBytes(file.size_bytes)}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => handleRemoveFile(file.id)}
                    className="flex-shrink-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
