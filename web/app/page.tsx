"use client";

import { useState, useCallback, useRef, useEffect } from "react";
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
  Fingerprint,
  Menu,
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

/* Navbar Component */
const Navbar = () => (
  <nav className="fixed left-0 right-0 top-0 z-50 border-b border-white/10 bg-white/50 backdrop-blur-md dark:bg-black/50">
    <div className="container mx-auto flex items-center justify-between px-6 py-4">
      <div className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-500 text-white">
          <Fingerprint className="h-5 w-5" />
        </div>
        <span className="text-xl font-bold tracking-tight text-surface-900 dark:text-white">
          OriginMark
        </span>
      </div>
      <div className="hidden items-center gap-8 text-sm font-medium text-surface-600 dark:text-surface-300 md:flex">
        <a href="#features" className="hover:text-primary-500">Features</a>
        <a href="#how-it-works" className="hover:text-primary-500">How it Works</a>
        <a href="https://github.com/krikera/originmark" target="_blank" className="hover:text-primary-500">GitHub</a>
      </div>
      <button className="md:hidden">
        <Menu className="h-6 w-6 text-surface-600 dark:text-surface-300" />
      </button>
    </div>
  </nav>
);

/* Mock Verification (Hero Visual) */
const MockVerificationCard = () => (
  <motion.div
    initial={{ opacity: 0, scale: 0.9, rotate: 2 }}
    animate={{ opacity: 1, scale: 1, rotate: 0 }}
    transition={{ duration: 0.8, delay: 0.2 }}
    className="relative mx-auto w-full max-w-sm rounded-3xl border border-surface-200 bg-white p-6 shadow-2xl dark:border-surface-700 dark:bg-surface-900/90 lg:mx-0"
  >
    {/* Decorative Elements */}
    <div className="absolute -right-12 -top-12 -z-10 h-64 w-64 rounded-full bg-primary-500/20 blur-3xl" />
    <div className="absolute -bottom-12 -left-12 -z-10 h-64 w-64 rounded-full bg-accent-500/20 blur-3xl" />

    {/* Header */}
    <div className="flex items-center justify-between border-b border-surface-100 pb-4 dark:border-surface-800">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 overflow-hidden rounded-full bg-surface-100">
          <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix" alt="Avatar" />
        </div>
        <div>
          <p className="text-sm font-semibold text-surface-900 dark:text-white">P</p>
          <p className="text-xs text-surface-500">Authorized Signer</p>
        </div>
      </div>
      <div className="rounded-full bg-green-100 px-3 py-1 text-xs font-bold text-green-700 dark:bg-green-900/30 dark:text-green-400">
        VERIFIED
      </div>
    </div>

    {/* Content Body */}
    <div className="py-6">
      <div className="mb-4 aspect-video w-full rounded-xl bg-surface-50 p-4 dark:bg-surface-800">
        <div className="flex h-full items-center justify-center text-surface-400">
          <FileSignature className="h-8 w-8 opacity-50" />
        </div>
      </div>
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs text-surface-500">Content Hash</span>
          <span className="font-mono text-xs text-surface-700 dark:text-surface-300">
            e7f9...8a2b
            <CheckCircle2 className="ml-1 inline h-3 w-3 text-green-500" />
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-surface-500">Timestamp</span>
          <span className="text-xs text-surface-700 dark:text-surface-300">
            Feb 26, 2026 • 14:32 UTC
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-surface-500">Model</span>
          <span className="text-xs font-medium text-primary-500">GPT-5</span>
        </div>
      </div>
    </div>

    {/* Footer Seal */}
    <div className="mt-2 flex items-center justify-center gap-2 rounded-lg bg-surface-50 py-3 text-xs font-medium text-surface-600 dark:bg-surface-800 dark:text-surface-400">
      <Shield className="h-4 w-4 text-primary-500" />
      Cryptographically Secured
    </div>
  </motion.div>
);

export default function Home() {
  const [mode, setMode] = useState<Mode>("sign");
  const [loading, setLoading] = useState(false);
  const [fileResults, setFileResults] = useState<FileResult[]>([]);
  const [metadata, setMetadata] = useState({ author: "", model_used: "" });
  const [batchMode, setBatchMode] = useState(false);
  const [isMainVisible, setIsMainVisible] = useState(false);
  const mainSectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (isMainVisible && mainSectionRef.current) {
      // Small timeout to ensure DOM is ready
      setTimeout(() => {
        mainSectionRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, [isMainVisible]);

  const handleStart = (selectedMode: Mode) => {
    setMode(selectedMode);
    setIsMainVisible(true);
  };

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
    <div className="min-h-screen bg-gradient-blobs">
      <Toaster
        position="top-right"
        toastOptions={{
          className: "!bg-surface-900 !text-white !border-surface-700",
        }}
      />

      <Navbar />

      {/* Hero Section */}
      <header className="relative pt-32 pb-20 sm:pt-40 sm:pb-32">
        <div className="container mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center xl:gap-20">
            {/* Left Column: Text */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6 }}
              className="max-w-2xl text-center lg:text-left"
            >
              {/* Badge */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="mb-6 inline-flex items-center gap-2 rounded-full border border-primary-500/30 bg-white/50 px-4 py-1.5 text-sm font-medium text-primary-700 backdrop-blur-sm dark:bg-white/5 dark:text-primary-300"
              >
                <Sparkles className="h-4 w-4 text-primary-500" />
                <span>The Standard for Content Provenance</span>
              </motion.div>

              {/* Title */}
              <h1 className="mb-6 font-display text-5xl font-bold tracking-tight text-surface-900 dark:text-white sm:text-6xl">
                Verify AI Content with <span className="gradient-text">Authenticity</span>
              </h1>

              {/* Subtitle */}
              <p className="mb-10 text-lg leading-relaxed text-surface-600 dark:text-surface-400 sm:text-xl">
                OriginMark adds an immutable cryptographic seal to your AI-generated content. Ensure trust, track provenance, and protect your reputation in an AI-driven world.
              </p>

              {/* CTA Buttons */}
              <div className="flex flex-col items-center gap-4 sm:flex-row lg:justify-start">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleStart("sign")}
                  className="btn-glow flex w-full items-center justify-center gap-2 sm:w-auto"
                >
                  <FileSignature className="h-5 w-5" />
                  Sign Content
                  <ArrowRight className="h-4 w-4" />
                </motion.button>

                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={() => handleStart("verify")}
                  className="btn-outline flex w-full items-center justify-center gap-2 bg-white/50 backdrop-blur-sm sm:w-auto dark:bg-black/20"
                >
                  <Shield className="h-5 w-5" />
                  Verify Authenticity
                </motion.button>
              </div>

              {/* Trust markers */}
              <div className="mt-10 flex items-center justify-center gap-6 text-sm text-surface-500 lg:justify-start">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary-500" />
                  <span>Ed25519 Security</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary-500" />
                  <span>Tamper-proof</span>
                </div>
              </div>
            </motion.div>

            {/* Right Column: Visual */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="relative hidden lg:block"
            >
              <MockVerificationCard />
            </motion.div>
          </div>
        </div>
      </header>

      {/* Main Content (Functional Area) */}
      <AnimatePresence>
        {isMainVisible && (
          <motion.main
            ref={mainSectionRef}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="container mx-auto px-4 pb-24 sm:px-6 lg:px-8"
            id="main-section"
          >

            <div className="mx-auto max-w-4xl py-12">
              <div className="mb-12 text-center">
                <h2 className="text-3xl font-bold text-surface-900 dark:text-white">
                  {mode === "sign" ? "Sign Your Content" : "Verify Authenticity"}
                </h2>
                <p className="mt-2 text-surface-600 dark:text-surface-400">
                  {mode === "sign"
                    ? "Upload your files to generate cryptographic signatures"
                    : "Upload files and signatures to verify their origin"}
                </p>
              </div>

              {/* Mode Switcher */}
              <motion.div
                layout
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
                        {m === "sign" ? "Sign Mode" : "Verify Mode"}
                      </span>
                    </button>
                  ))}
                </div>
              </motion.div>

              {/* Batch Toggle */}
              <motion.div
                layout
                className="mb-6 flex justify-center"
              >
                <label className="glass-card flex cursor-pointer items-center gap-3 px-5 py-3 transition-colors hover:bg-white/20 dark:hover:bg-white/5">
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
                layout
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
                          Author Identity
                        </label>
                        <input
                          type="text"
                          value={metadata.author}
                          onChange={(e) =>
                            setMetadata({ ...metadata, author: e.target.value })
                          }
                          className="input-modern"
                          placeholder="e.g. Alice Freeman"
                        />
                      </div>
                      <div>
                        <label className="mb-2 block text-sm font-medium text-surface-700 dark:text-surface-300">
                          AI Model / Source
                        </label>
                        <div className="relative">
                          <input
                            type="text"
                            value={metadata.model_used}
                            onChange={(e) =>
                              setMetadata({ ...metadata, model_used: e.target.value })
                            }
                            className="input-modern"
                            placeholder="e.g. V0, ChatGPT, Midjourney"
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
                          Processing cryptographic operations...
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
                                ? `Drag & drop multiple files to ${mode}`
                                : `Drag & drop a file to ${mode}`}
                          </p>
                          <p className="mt-2 text-sm text-surface-500">
                            {mode === "sign"
                              ? "Supported: Text, Markdown, Images, Code"
                              : "Upload any artifact to verify its digital signature"}
                          </p>
                        </div>
                        <button
                          type="button"
                          className="inline-flex items-center gap-2 text-sm font-medium text-primary-500 hover:text-primary-600 dark:text-primary-400"
                        >
                          <span>Browse Files</span>
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
                          Processed ({fileResults.length})
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
                                <span className="font-medium truncate max-w-[200px]">{fileResult.file.name}</span>
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
            </div>
          </motion.main>
        )}
      </AnimatePresence>

      {/* Features Grid below main content if not visible, or below it if visible */}
      <div className="container mx-auto px-6 py-24" id="features">
        <h2 className="mb-12 text-center text-3xl font-bold text-surface-900 dark:text-white">Why OriginMark?</h2>
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="grid gap-8 sm:grid-cols-3"
        >
          {[
            {
              icon: Zap,
              title: "Batch Processing",
              description:
                "Process multiple files at once with highly efficient parallel Ed25519 signing and verification.",
            },
            {
              icon: Lock,
              title: "Cryptographic Trust",
              description:
                "Uses industry-standard cryptographic signatures. Signatures are immutable and verifiable offline.",
            },
            {
              icon: Globe,
              title: "Universal Extension",
              description:
                "Verify content anywhere on the web with our browser extension. One click provenance verification.",
            },
          ].map((feature, i) => (
            <motion.div
              key={feature.title}
              whileHover={{ y: -5 }}
              className="feature-card"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary-500/10 text-primary-500">
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="mb-2 text-lg font-semibold text-surface-900 dark:text-white">
                {feature.title}
              </h3>
              <p className="text-sm leading-relaxed text-surface-600 dark:text-surface-400">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </motion.div>
      </div>

      {/* Footer */}
      <footer className="border-t border-surface-200 py-12 dark:border-surface-800">
        <div className="container mx-auto px-6 flex flex-col items-center justify-between gap-4 md:flex-row">
          <div className="flex items-center gap-2">
            <Fingerprint className="h-5 w-5 text-surface-400" />
            <span className="text-sm text-surface-500">© {new Date().getFullYear()} OriginMark</span>
          </div>
          <div className="flex gap-6 text-sm text-surface-500">
            <a href="#" className="hover:text-primary-500">Privacy</a>
            <a href="#" className="hover:text-primary-500">Terms</a>
            <a href="https://github.com/krikera/originmark" className="hover:text-primary-500">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}