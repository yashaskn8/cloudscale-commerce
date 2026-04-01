import React, { useRef, useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Upload, X, File, Image } from "lucide-react";

interface FileUploadProps {
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // bytes
  maxFiles?: number;
  onFilesChange?: (files: File[]) => void;
  label?: string;
  hint?: string;
  error?: string;
  disabled?: boolean;
  className?: string;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function FileUpload({
  accept,
  multiple = false,
  maxSize = 10 * 1024 * 1024,
  maxFiles = 5,
  onFilesChange,
  label = "Upload files",
  hint,
  error,
  disabled,
  className,
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const addFiles = useCallback(
    (newFiles: FileList | File[]) => {
      setFileError(null);
      const arr = Array.from(newFiles);
      const oversized = arr.find((f) => f.size > maxSize);
      if (oversized) {
        setFileError(`${oversized.name} exceeds ${formatSize(maxSize)} limit`);
        return;
      }
      const merged = multiple ? [...files, ...arr].slice(0, maxFiles) : [arr[0]];
      setFiles(merged);
      onFilesChange?.(merged);
    },
    [files, maxSize, maxFiles, multiple, onFilesChange]
  );

  const removeFile = (index: number) => {
    const updated = files.filter((_, i) => i !== index);
    setFiles(updated);
    onFilesChange?.(updated);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (!disabled) addFiles(e.dataTransfer.files);
  };

  const isImage = (name: string) => /\.(jpg|jpeg|png|gif|webp|svg)$/i.test(name);

  return (
    <div className={cn("w-full space-y-2", className)}>
      {label && <p className="text-sm font-medium text-foreground">{label}</p>}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => !disabled && inputRef.current?.click()}
        className={cn(
          "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 cursor-pointer transition-colors",
          dragOver ? "border-primary bg-primary/5" : "border-input hover:border-primary/50 hover:bg-accent/30",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <Upload className="h-8 w-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          <span className="font-semibold text-primary">Click to upload</span> or drag & drop
        </p>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          onChange={(e) => e.target.files && addFiles(e.target.files)}
          className="sr-only"
          disabled={disabled}
        />
      </div>

      {(error || fileError) && (
        <p className="text-xs text-destructive" role="alert">{error || fileError}</p>
      )}

      {files.length > 0 && (
        <ul className="space-y-1">
          {files.map((f, i) => (
            <li key={i} className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
              {isImage(f.name) ? <Image className="h-4 w-4 text-blue-500" /> : <File className="h-4 w-4 text-muted-foreground" />}
              <span className="flex-1 truncate text-foreground">{f.name}</span>
              <span className="text-xs text-muted-foreground">{formatSize(f.size)}</span>
              <button onClick={() => removeFile(i)} className="text-muted-foreground hover:text-destructive" aria-label={`Remove ${f.name}`}>
                <X className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
