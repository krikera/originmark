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
  Code2,

  Tags,
  Boxes,
  ArrowUpRight,
  Github,
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

/* ═══════════════════════════════════════════
   ANIMATED HERO VISUAL — Shield with rings
   ═══════════════════════════════════════════ */
const AnimatedShield = () => (
  <div className="relative mx-auto flex h-72 w-72 items-center justify-center sm:h-80 sm:w-80 lg:h-96 lg:w-96">
    {/* Outer breathing ring */}
    <motion.div
      animate={{ scale: [1, 1.08, 1], opacity: [0.15, 0.3, 0.15] }}
      transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
      className="absolute inset-0 rounded-full border border-accent-500/20"
    />
    {/* Middle ring */}
    <motion.div
      animate={{ scale: [1, 1.05, 1], opacity: [0.2, 0.4, 0.2] }}
      transition={{ duration: 3.5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
      className="absolute inset-8 rounded-full border border-accent-500/25"
    />
    {/* Inner glow ring */}
    <motion.div
      animate={{ scale: [1, 1.03, 1], opacity: [0.3, 0.6, 0.3] }}
      transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 1 }}
      className="absolute inset-16 rounded-full border border-accent-500/30 shadow-glow"
    />
    {/* Center shield icon */}
    <motion.div
      initial={{ opacity: 0, scale: 0.5 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.8, delay: 0.3 }}
      className="relative z-10 flex h-28 w-28 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-500 to-primary-700 shadow-glow-lg sm:h-32 sm:w-32"
    >
      <Fingerprint className="h-14 w-14 text-surface-950 sm:h-16 sm:w-16" />
    </motion.div>

    {/* Floating data particles */}
    {[...Array(6)].map((_, i) => (
      <motion.div
        key={i}
        className="absolute h-1.5 w-1.5 rounded-full bg-accent-500"
        style={{
          top: `${20 + Math.random() * 60}%`,
          left: `${20 + Math.random() * 60}%`,
        }}
        animate={{
          y: [0, -15 - Math.random() * 20, 0],
          opacity: [0.2, 0.7, 0.2],
        }}
        transition={{
          duration: 3 + Math.random() * 2,
          repeat: Infinity,
          delay: i * 0.5,
          ease: "easeInOut",
        }}
      />
    ))}
  </div>
);

/* ═══════════════════════════════
   NAVBAR
   ═══════════════════════════════ */
const Navbar = () => (
  <nav className="fixed left-0 right-0 top-0 z-50 border-b border-white/[0.06] bg-surface-950/80 backdrop-blur-xl">
    <div className="container mx-auto flex items-center justify-between px-6 py-4">
      <div className="flex items-center gap-2.5">
        <div className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg">
          <img src="/favi.png" alt="OriginMark" className="h-full w-full object-contain" />
        </div>
        <span className="font-display text-lg font-bold tracking-tight text-white">
          OriginMark
        </span>
      </div>
      <div className="hidden items-center gap-8 text-sm font-medium text-surface-300 md:flex">
        <a href="#features" className="transition-colors hover:text-accent-500">Features</a>
        <a href="#how-it-works" className="transition-colors hover:text-accent-500">How it Works</a>
        <a
          href="https://github.com/krikera/originmark"
          target="_blank"
          className="flex items-center gap-1.5 transition-colors hover:text-accent-500"
        >
          <Github className="h-4 w-4" />
          GitHub
        </a>
      </div>
      <button className="text-surface-400 md:hidden">
        <Menu className="h-6 w-6" />
      </button>
    </div>
  </nav>
);

/* ═══════════════════════════════
   MAIN PAGE
   ═══════════════════════════════ */
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
      setTimeout(() => {
        mainSectionRef.current?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    }
  }, [isMainVisible]);

  const handleStart = (selectedMode: Mode) => {
    setMode(selectedMode);
    setIsMainVisible(true);

    setTimeout(() => {
      mainSectionRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
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
    <div className="relative min-h-screen">
      <Toaster
        position="top-right"
        toastOptions={{
          className: "!bg-surface-900 !text-white !border-surface-700",
        }}
      />

      <Navbar />

      {/* ═══════════════════════════════
          HERO SECTION
         ═══════════════════════════════ */}
      <header className="relative overflow-hidden pt-28 pb-16 sm:pt-36 sm:pb-24">
        {/* Accent glow behind hero */}
        <div className="pointer-events-none absolute left-1/2 top-1/3 -z-10 h-[500px] w-[800px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-accent-500/[0.07] blur-[120px]" />

        <div className="container mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center xl:gap-20">
            {/* Left Column: Text */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7 }}
              className="max-w-2xl text-center lg:text-left"
            >
              {/* Badge */}
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="mb-6 inline-flex items-center gap-2 rounded-full border border-accent-500/20 bg-accent-500/[0.06] px-4 py-1.5 text-sm font-medium text-accent-400"
              >
                <Sparkles className="h-4 w-4" />
                <span>Open-Source Content Provenance</span>
              </motion.div>

              {/* Headline */}
              <h1 className="mb-6 font-display text-4xl font-bold tracking-tight text-white sm:text-5xl lg:text-6xl">
                Prove the Origin of{" "}
                <span className="gradient-text">AI Content</span>
              </h1>

              {/* Subtitle */}
              <p className="mb-10 text-base leading-relaxed text-surface-300 sm:text-lg">
                OriginMark adds an immutable cryptographic seal to any AI-generated
                artifact. Sign it. Ship it. Let anyone verify it instantly.
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
                  className="btn-outline flex w-full items-center justify-center gap-2 sm:w-auto"
                >
                  <Shield className="h-5 w-5" />
                  Verify Authenticity
                </motion.button>
              </div>

              {/* Trust markers */}
              <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-surface-400 lg:justify-start">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-accent-500" />
                  <span>Ed25519 Signatures</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-accent-500" />
                  <span>Tamper-proof</span>
                </div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-accent-500" />
                  <span>Offline Verifiable</span>
                </div>
              </div>
            </motion.div>

            {/* Right Column: Animated Shield */}
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.8, delay: 0.3 }}
              className="flex justify-center"
            >
              <AnimatedShield />
            </motion.div>
          </div>
        </div>
      </header>

      {/* ═══════════════════════════════
          STATS / SOCIAL PROOF BAR
         ═══════════════════════════════ */}
      <section className="border-y border-white/[0.06] bg-surface-950/50 backdrop-blur-sm">
        <div className="container mx-auto max-w-6xl px-6 py-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-2 gap-6 sm:grid-cols-4"
          >
            {[
              { label: "Open Source", value: "100%", icon: Code2 },
              { label: "Encryption", value: "Ed25519", icon: Lock },
              { label: "Tamper Proof", value: "Always", icon: Shield },
              { label: "Verification", value: "Instant", icon: Zap },
            ].map((stat) => (
              <div key={stat.label} className="flex items-center gap-3 justify-center sm:justify-start">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-accent-500/10">
                  <stat.icon className="h-5 w-5 text-accent-500" />
                </div>
                <div>
                  <p className="text-sm font-bold text-white">{stat.value}</p>
                  <p className="text-xs text-surface-400">{stat.label}</p>
                </div>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════
          FUNCTIONAL AREA (Sign/Verify)
         ═══════════════════════════════ */}
      <AnimatePresence>
        {isMainVisible && (
          <motion.main
            ref={mainSectionRef}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="container mx-auto px-4 pb-24 pt-24 sm:px-6 lg:px-8"
            id="main-section"
          >

            <div className="mx-auto max-w-4xl py-12">
              <div className="mb-12 text-center">
                <h2 className="font-display text-3xl font-bold text-white">
                  {mode === "sign" ? "Sign Your Content" : "Verify Authenticity"}
                </h2>
                <p className="mt-2 text-surface-400">
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
                          ? "text-surface-950"
                          : "text-surface-400 hover:text-white"
                      )}
                    >
                      {mode === m && (
                        <motion.div
                          layoutId="activeTab"
                          className="absolute inset-0 rounded-xl bg-gradient-to-r from-accent-500 to-accent-600"
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
                <label className="glass-card flex cursor-pointer items-center gap-3 px-5 py-3 transition-colors hover:bg-white/[0.04]">
                  <input
                    type="checkbox"
                    checked={batchMode}
                    onChange={(e) => setBatchMode(e.target.checked)}
                    className="h-5 w-5 rounded-md border-surface-600 bg-surface-800 text-accent-500 focus:ring-2 focus:ring-accent-500 focus:ring-offset-0"
                  />
                  <span className="text-sm font-medium text-surface-300">
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
                        <label className="mb-2 block text-sm font-medium text-surface-300">
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
                        <label className="mb-2 block text-sm font-medium text-surface-300">
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
                        <Loader2 className="h-12 w-12 animate-spin text-accent-500" />
                        <p className="text-surface-400">
                          Processing cryptographic operations...
                        </p>
                      </motion.div>
                    ) : (
                      <>
                        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-accent-500/10 text-accent-500 transition-all duration-300 group-hover:scale-110 group-hover:bg-accent-500/20">
                          <Upload className="h-8 w-8" />
                        </div>
                        <div>
                          <p className="text-lg font-medium text-surface-200">
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
                          className="inline-flex items-center gap-2 text-sm font-medium text-accent-500 hover:text-accent-400"
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
                        <h3 className="text-lg font-semibold text-white">
                          Processed ({fileResults.length})
                        </h3>
                        <div className="flex gap-2">
                          {mode === "sign" && fileResults.some((f) => f.result) && (
                            <motion.button
                              whileHover={{ scale: 1.02 }}
                              whileTap={{ scale: 0.98 }}
                              onClick={downloadAllResults}
                              className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-surface-950 transition-colors hover:bg-accent-400"
                            >
                              <Download className="h-4 w-4" />
                              Download All
                            </motion.button>
                          )}
                          <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={clearResults}
                            className="flex items-center gap-2 rounded-lg bg-surface-800 px-4 py-2 text-sm font-medium text-surface-300 transition-colors hover:bg-surface-700"
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
                                  : ""
                            )}
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3">
                                {fileResult.processing ? (
                                  <Loader2 className="h-5 w-5 animate-spin text-accent-500" />
                                ) : fileResult.error ? (
                                  <XCircle className="h-5 w-5 text-red-400" />
                                ) : (
                                  <CheckCircle2 className="h-5 w-5 text-accent-500" />
                                )}
                                <span className="font-medium truncate max-w-[200px] text-white">{fileResult.file.name}</span>
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
                                  <span className="font-medium text-surface-300">Hash:</span>
                                  <span className="font-mono text-xs text-surface-400">
                                    {fileResult.result.content_hash?.slice(0, 32)}...
                                  </span>
                                </div>
                                {fileResult.result.metadata?.author && (
                                  <div className="flex gap-2">
                                    <span className="font-medium text-surface-300">Author:</span>
                                    <span className="text-surface-400">{fileResult.result.metadata.author}</span>
                                  </div>
                                )}
                                {fileResult.result.metadata?.model_used && (
                                  <div className="flex gap-2">
                                    <span className="font-medium text-surface-300">Model:</span>
                                    <span className="text-surface-400">{fileResult.result.metadata.model_used}</span>
                                  </div>
                                )}
                              </div>
                            )}

                            {fileResult.error && (
                              <p className="mt-2 text-sm text-red-400">{fileResult.error}</p>
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

      {/* ═══════════════════════════════
          HOW IT WORKS
         ═══════════════════════════════ */}
      <section className="relative py-24 sm:py-32" id="how-it-works">
        <div className="container mx-auto max-w-5xl px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-16 text-center"
          >
            <h2 className="font-display text-3xl font-bold text-white sm:text-4xl">
              How it Works
            </h2>
            <p className="mt-4 text-surface-400 sm:text-lg">
              Three simple steps to provable content authenticity.
            </p>
          </motion.div>

          <div className="grid gap-8 sm:grid-cols-3">
            {[
              {
                step: 1,
                icon: Upload,
                title: "Upload Content",
                description:
                  "Upload any AI-generated text, image, or code artifact. Drag & drop or browse.",
              },
              {
                step: 2,
                icon: FileSignature,
                title: "Generate Signature",
                description:
                  "We compute a SHA-256 hash and sign it with Ed25519, embedding provenance metadata.",
              },
              {
                step: 3,
                icon: CheckCircle2,
                title: "Verify Anywhere",
                description:
                  "Share the sidecar JSON. Anyone can verify the signature — no account needed.",
              },
            ].map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: i * 0.15 }}
                className="step-card"
              >
                <div className="step-number">{item.step}</div>
                <div className="mb-3 flex justify-center">
                  <item.icon className="h-6 w-6 text-accent-500" />
                </div>
                <h3 className="mb-2 font-display text-lg font-semibold text-white">
                  {item.title}
                </h3>
                <p className="text-sm leading-relaxed text-surface-400">
                  {item.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════
          FEATURES GRID
         ═══════════════════════════════ */}
      <section className="py-24 sm:py-32" id="features">
        <div className="container mx-auto max-w-6xl px-6">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="mb-16 text-center"
          >
            <h2 className="font-display text-3xl font-bold text-white sm:text-4xl">
              Why OriginMark?
            </h2>
            <p className="mt-4 text-surface-400 sm:text-lg">
              Built for the AI era. From individual creators to enterprise pipelines.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3"
          >
            {[
              {
                icon: Zap,
                title: "Batch Processing",
                description:
                  "Process hundreds of files at once with parallel Ed25519 signing and verification.",
              },
              {
                icon: Lock,
                title: "Cryptographic Trust",
                description:
                  "Industry-standard Ed25519 signatures — immutable, verifiable offline, and future-proof.",
              },
              {
                icon: Globe,
                title: "Browser Extension",
                description:
                  "Verify content anywhere on the web with one click. No downloads, no accounts.",
              },
              {
                icon: Boxes,
                title: "Open Standard",
                description:
                  "C2PA-aligned metadata format. Interoperable with the content provenance ecosystem.",
              },
              {
                icon: Tags,
                title: "Metadata Tracking",
                description:
                  "Embed author identity, AI model, timestamp, and custom fields in every signature.",
              },
              {
                icon: Code2,
                title: "API-First",
                description:
                  "RESTful API and SDKs for TypeScript, Python, and CLI. Integrate in minutes.",
              },
            ].map((feature) => (
              <motion.div
                key={feature.title}
                whileHover={{ y: -4 }}
                className="feature-card"
              >
                <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-accent-500/10 text-accent-500">
                  <feature.icon className="h-6 w-6" />
                </div>
                <h3 className="mb-2 font-display text-lg font-semibold text-white">
                  {feature.title}
                </h3>
                <p className="text-sm leading-relaxed text-surface-400">
                  {feature.description}
                </p>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* ═══════════════════════════════
          FOOTER
         ═══════════════════════════════ */}
      <footer className="border-t border-white/[0.06] py-16">
        <div className="container mx-auto max-w-6xl px-6">
          <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
            {/* Brand */}
            <div className="sm:col-span-2 lg:col-span-1">
              <div className="mb-4 flex items-center gap-2.5">
                <div className="flex h-7 w-7 items-center justify-center overflow-hidden rounded-lg">
                  <img src="/favi.png" alt="OriginMark" className="h-full w-full object-contain" />
                </div>
                <span className="font-display text-lg font-bold text-white">OriginMark</span>
              </div>
              <p className="text-sm leading-relaxed text-surface-500">
                Open-source cryptographic signatures for AI-generated content. Trust what you read.
              </p>
            </div>

            {/* Product */}
            <div>
              <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-surface-400">
                Product
              </h4>
              <ul className="space-y-2.5 text-sm text-surface-500">
                <li><a href="#features" className="transition-colors hover:text-accent-500">Features</a></li>
                <li><a href="#how-it-works" className="transition-colors hover:text-accent-500">How it Works</a></li>
                <li><a href="#main-section" className="transition-colors hover:text-accent-500">Try it Now</a></li>
              </ul>
            </div>

            {/* Resources */}
            <div>
              <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-surface-400">
                Resources
              </h4>
              <ul className="space-y-2.5 text-sm text-surface-500">
                <li>
                  <a
                    href="https://github.com/krikera/originmark"
                    target="_blank"
                    className="inline-flex items-center gap-1 transition-colors hover:text-accent-500"
                  >
                    GitHub <ArrowUpRight className="h-3 w-3" />
                  </a>
                </li>
                <li><a href="#" className="transition-colors hover:text-accent-500">Documentation</a></li>
                <li><a href="#" className="transition-colors hover:text-accent-500">API Reference</a></li>
              </ul>
            </div>

            {/* Legal */}
            <div>
              <h4 className="mb-4 text-sm font-semibold uppercase tracking-wider text-surface-400">
                Legal
              </h4>
              <ul className="space-y-2.5 text-sm text-surface-500">
                <li><a href="#" className="transition-colors hover:text-accent-500">Privacy Policy</a></li>
                <li><a href="#" className="transition-colors hover:text-accent-500">Terms of Service</a></li>
                <li><a href="#" className="transition-colors hover:text-accent-500">License (MIT)</a></li>
              </ul>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-white/[0.06] pt-8 sm:flex-row">
            <p className="text-sm text-surface-500">
              © {new Date().getFullYear()} OriginMark. Open source under MIT License.
            </p>
            <a
              href="https://github.com/krikera/originmark"
              target="_blank"
              className="inline-flex items-center gap-2 text-sm text-surface-500 transition-colors hover:text-accent-500"
            >
              <Github className="h-4 w-4" />
              Star on GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}