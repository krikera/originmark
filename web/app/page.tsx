"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { toast, Toaster } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import axios from "axios";
import {
  Upload,
  Shield,
  CheckCircle2,
  XCircle,
  FileSignature,
  Sparkles,
  Zap,
  Lock,
  Globe,
  ArrowRight,
  Loader2,
  Download,
  Trash2,
  ChevronDown,
} from "lucide-react";
import { clsx } from "clsx";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FileResult {
  file: File;
  result?: SignatureResult | VerificationResult;
  error?: string;
  processing?: boolean;
}

interface SignatureResult {
  id: string;
  content_hash: string;
  signature: string;
  public_key: string;
  metadata?: {
    author?: string;
    model_used?: string;
    timestamp?: string;
  };
}

interface VerificationResult {
  valid: boolean;
  message: string;
  content_hash: string;
  metadata?: {
    author?: string;
    model_used?: string;
    timestamp?: string;
  };
}

type Mode = "sign" | "verify";

export default function Home() {
  const [mode, setMode] = useState<Mode>("sign");
  const [loading, setLoading] = useState(false);
  const [fileResults, setFileResults] = useState<FileResult[]>([]);
  const [metadata, setMetadata] = useState({ author: "", model_used: "" });
  const [batchMode, setBatchMode] = useState(false);

  const processFile = useCallback(
    async (file: File): Promise<SignatureResult | VerificationResult> => {
      const formData = new FormData();
      formData.append("file", file);

      if (mode === "sign") {
        if (metadata.author) formData.append("author", metadata.author);
        if (metadata.model_used) formData.append("model_used", metadata.model_used);
      }

      const endpoint = mode === "sign" ? "/sign" : "/verify";
      const response = await axios.post(`${API_URL}${endpoint}`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      return response.data;
    },
    [mode, metadata]
  );

  const downloadSidecar = useCallback((file: File, result: SignatureResult) => {
    const content = JSON.stringify(result, null, 2);
    const blob = new Blob([content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${file.name}.originmark.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const isBatch = acceptedFiles.length > 1 || batchMode;
      if (isBatch) setBatchMode(true);

      const initialResults: FileResult[] = acceptedFiles.map((file) => ({
        file,
        processing: true,
      }));
      setFileResults(initialResults);
      setLoading(true);

      for (let i = 0; i < acceptedFiles.length; i++) {
        const file = acceptedFiles[i];

        try {
          const result = await processFile(file);

          setFileResults((prev) =>
            prev.map((item, idx) =>
              idx === i ? { ...item, processing: false, result } : item
            )
          );

          if (!isBatch && mode === "sign") {
            downloadSidecar(file, result as SignatureResult);
          }
        } catch (error) {
          const message = error instanceof Error ? error.message : "An error occurred";
          setFileResults((prev) =>
            prev.map((item, idx) =>
              idx === i ? { ...item, processing: false, error: message } : item
            )
          );
        }
      }

      setLoading(false);

      const successCount = acceptedFiles.length;
      if (mode === "sign") {
        toast.success(`${successCount} file${successCount > 1 ? "s" : ""} signed successfully!`);
      } else {
        toast.success(`Verification complete for ${successCount} file${successCount > 1 ? "s" : ""}`);
      }
    },
    [batchMode, mode, processFile, downloadSidecar]
  );

  const downloadAllResults = useCallback(() => {
    const successfulResults = fileResults.filter(
      (item): item is FileResult & { result: SignatureResult } =>
        item.result !== undefined && !("valid" in item.result)
    );

    successfulResults.forEach(({ file, result }) => {
      downloadSidecar(file, result);
    });

    toast.success("All signature files downloaded!");
  }, [fileResults, downloadSidecar]);

  const clearResults = useCallback(() => {
    setFileResults([]);
    setBatchMode(false);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept:
      mode === "sign"
        ? {
          "text/*": [".txt", ".md"],
          "image/*": [".png", ".jpg", ".jpeg", ".gif", ".webp"],
        }
        : undefined,
  });

  return (
    <div className="min-h-screen">
      <Toaster
        position="top-right"
        toastOptions={{
          className: "!bg-surface-900 !text-white !border-surface-700",
        }}
      />

      {/* Hero Section */}
      <header className="relative overflow-hidden pt-16 pb-20 sm:pt-24 sm:pb-32">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="mx-auto max-w-4xl text-center"
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1 }}
              className="mb-8 inline-flex items-center gap-2 rounded-full border border-primary-500/30 bg-primary-500/10 px-4 py-2 text-sm font-medium text-primary-600 dark:text-primary-400"
            >
              <Sparkles className="h-4 w-4" />
              Cryptographic Content Provenance
            </motion.div>

            {/* Title */}
            <h1 className="mb-6 font-display text-5xl font-bold tracking-tight text-surface-900 dark:text-white sm:text-6xl lg:text-7xl">
              <span className="block">Verify AI Content</span>
              <span className="gradient-text">with Confidence</span>
            </h1>

            {/* Subtitle */}
            <p className="mx-auto mb-10 max-w-2xl text-lg text-surface-600 dark:text-surface-400 sm:text-xl">
              Sign and verify AI-generated content using Ed25519 cryptographic
              signatures. Ensure authenticity and build trust in AI outputs.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setMode("sign")}
                className="btn-glow flex items-center gap-2"
              >
                <FileSignature className="h-5 w-5" />
                Start Signing
                <ArrowRight className="h-4 w-4" />
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setMode("verify")}
                className="btn-outline flex items-center gap-2"
              >
                <Shield className="h-5 w-5" />
                Verify Content
              </motion.button>
            </div>
          </motion.div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 pb-24 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl">
          {/* Mode Switcher */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mb-8 flex justify-center"
          >
            <div className="glass-card inline-flex p-1.5">
              {(["sign", "verify"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={clsx(
                    "relative rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-300",
                    mode === m
                      ? "text-white"
                      : "text-surface-600 hover:text-surface-900 dark:text-surface-400 dark:hover:text-white"
                  )}
                >
                  {mode === m && (
                    <motion.div
                      layoutId="activeTab"
                      className="absolute inset-0 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600"
                      transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                    />
                  )}
                  <span className="relative z-10 flex items-center gap-2">
                    {m === "sign" ? (
                      <FileSignature className="h-4 w-4" />
                    ) : (
                      <Shield className="h-4 w-4" />
                    )}
                    {m === "sign" ? "Sign Content" : "Verify Content"}
                  </span>
                </button>
              ))}
            </div>
          </motion.div>

          {/* Batch Toggle */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="mb-6 flex justify-center"
          >
            <label className="glass-card flex cursor-pointer items-center gap-3 px-5 py-3">
              <input
                type="checkbox"
                checked={batchMode}
                onChange={(e) => setBatchMode(e.target.checked)}
                className="h-5 w-5 rounded-md border-surface-300 bg-white text-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-offset-0 dark:border-surface-600 dark:bg-surface-800"
              />
              <span className="text-sm font-medium text-surface-700 dark:text-surface-300">
                Batch Processing Mode
              </span>
            </label>
          </motion.div>

          {/* Main Card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="glass-card p-8"
          >
            {/* Metadata Fields (Sign Mode) */}
            <AnimatePresence mode="wait">
              {mode === "sign" && (
                <motion.div
                  key="metadata"
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="mb-8 grid gap-4 sm:grid-cols-2"
                >
                  <div>
                    <label className="mb-2 block text-sm font-medium text-surface-700 dark:text-surface-300">
                      Author
                    </label>
                    <input
                      type="text"
                      value={metadata.author}
                      onChange={(e) =>
                        setMetadata({ ...metadata, author: e.target.value })
                      }
                      className="input-modern"
                      placeholder="Your name or organization"
                    />
                  </div>
                  <div>
                    <label className="mb-2 block text-sm font-medium text-surface-700 dark:text-surface-300">
                      AI Model Used
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={metadata.model_used}
                        onChange={(e) =>
                          setMetadata({ ...metadata, model_used: e.target.value })
                        }
                        className="input-modern"
                        placeholder="e.g., GPT-4, Claude 3, DALL-E 3"
                      />
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Dropzone */}
            <div
              {...getRootProps()}
              className={clsx(
                "dropzone group p-12 text-center",
                isDragActive && "active"
              )}
            >
              <input {...getInputProps()} />

              <div className="space-y-4">
                {loading ? (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex flex-col items-center gap-4"
                  >
                    <Loader2 className="h-12 w-12 animate-spin text-primary-500" />
                    <p className="text-surface-600 dark:text-surface-400">
                      Processing files...
                    </p>
                  </motion.div>
                ) : (
                  <>
                    <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-500/10 text-primary-500 transition-all duration-300 group-hover:scale-110 group-hover:bg-primary-500/20">
                      <Upload className="h-8 w-8" />
                    </div>
                    <div>
                      <p className="text-lg font-medium text-surface-800 dark:text-surface-200">
                        {isDragActive
                          ? "Drop files here..."
                          : batchMode
                            ? `Drag & drop files to ${mode}`
                            : `Drag & drop a file to ${mode}`}
                      </p>
                      <p className="mt-2 text-sm text-surface-500">
                        {mode === "sign"
                          ? "Supports .txt, .md, .png, .jpg, .gif, .webp"
                          : "Upload any file to verify its signature"}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="inline-flex items-center gap-2 text-sm font-medium text-primary-500 hover:text-primary-600 dark:text-primary-400"
                    >
                      <span>or click to browse</span>
                      <ChevronDown className="h-4 w-4" />
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* Results */}
            <AnimatePresence>
              {fileResults.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  className="mt-8"
                >
                  {/* Results Header */}
                  <div className="mb-4 flex items-center justify-between">
                    <h3 className="text-lg font-semibold text-surface-900 dark:text-white">
                      Results ({fileResults.length} file{fileResults.length > 1 ? "s" : ""})
                    </h3>
                    <div className="flex gap-2">
                      {mode === "sign" && fileResults.some((f) => f.result) && (
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={downloadAllResults}
                          className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-600"
                        >
                          <Download className="h-4 w-4" />
                          Download All
                        </motion.button>
                      )}
                      <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={clearResults}
                        className="flex items-center gap-2 rounded-lg bg-surface-200 px-4 py-2 text-sm font-medium text-surface-700 transition-colors hover:bg-surface-300 dark:bg-surface-700 dark:text-surface-200 dark:hover:bg-surface-600"
                      >
                        <Trash2 className="h-4 w-4" />
                        Clear
                      </motion.button>
                    </div>
                  </div>

                  {/* Results List */}
                  <div className="max-h-96 space-y-3 overflow-y-auto scrollbar-thin">
                    {fileResults.map((fileResult, index) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className={clsx(
                          "result-card",
                          fileResult.result && !fileResult.error
                            ? "valid" in fileResult.result
                              ? fileResult.result.valid
                                ? "success"
                                : "error"
                              : "success"
                            : fileResult.error
                              ? "error"
                              : "border-surface-200 bg-surface-50 dark:border-surface-700 dark:bg-surface-800/50"
                        )}
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            {fileResult.processing ? (
                              <Loader2 className="h-5 w-5 animate-spin text-primary-500" />
                            ) : fileResult.error ? (
                              <XCircle className="h-5 w-5 text-red-500" />
                            ) : (
                              <CheckCircle2 className="h-5 w-5 text-accent-500" />
                            )}
                            <span className="font-medium">{fileResult.file.name}</span>
                          </div>
                          {fileResult.result && !fileResult.error && (
                            <span className="badge badge-accent">
                              {"valid" in fileResult.result
                                ? fileResult.result.valid
                                  ? "Verified"
                                  : "Failed"
                                : "Signed"}
                            </span>
                          )}
                        </div>

                        {/* Result Details */}
                        {fileResult.result && !fileResult.error && (
                          <div className="mt-3 space-y-2 text-sm">
                            <div className="flex gap-2">
                              <span className="font-medium">Hash:</span>
                              <span className="font-mono text-xs opacity-70">
                                {fileResult.result.content_hash?.slice(0, 32)}...
                              </span>
                            </div>
                            {fileResult.result.metadata?.author && (
                              <div className="flex gap-2">
                                <span className="font-medium">Author:</span>
                                <span>{fileResult.result.metadata.author}</span>
                              </div>
                            )}
                            {fileResult.result.metadata?.model_used && (
                              <div className="flex gap-2">
                                <span className="font-medium">Model:</span>
                                <span>{fileResult.result.metadata.model_used}</span>
                              </div>
                            )}
                          </div>
                        )}

                        {fileResult.error && (
                          <p className="mt-2 text-sm">{fileResult.error}</p>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>

          {/* Features Grid */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="mt-16 grid gap-6 sm:grid-cols-3"
          >
            {[
              {
                icon: Zap,
                title: "Batch Processing",
                description:
                  "Process multiple files at once with efficient batch signing and verification",
              },
              {
                icon: Lock,
                title: "Ed25519 Signatures",
                description:
                  "Industry-standard cryptographic signatures for content authenticity",
              },
              {
                icon: Globe,
                title: "Browser Extension",
                description:
                  "Verify content directly from web pages with our Chrome extension",
              },
            ].map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 + i * 0.1 }}
                className="feature-card"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-500/10 text-primary-500">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 text-lg font-semibold text-surface-900 dark:text-white">
                  {feature.title}
                </h3>
                <p className="text-sm text-surface-600 dark:text-surface-400">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-200 py-8 dark:border-surface-800">
        <div className="container mx-auto px-4 text-center text-sm text-surface-500">
          <p>© {new Date().getFullYear()} OriginMark. Open source content provenance.</p>
        </div>
      </footer>
    </div>
  );
}