import type { Metadata, Viewport } from "next";
import { Inter, Outfit, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

const outfit = Outfit({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-outfit",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-jetbrains",
});

export const metadata: Metadata = {
  metadataBase: new URL("https://originmark.dev"),
  title: {
    default: "OriginMark - Digital Signature Verification for AI Content",
    template: "%s | OriginMark",
  },
  description:
    "Sign and verify AI-generated content with cryptographic Ed25519 signatures. Ensure authenticity and traceability of AI outputs.",
  keywords: [
    "AI content verification",
    "digital signature",
    "Ed25519",
    "AI authenticity",
    "content provenance",
    "C2PA",
    "AI transparency",
  ],
  authors: [{ name: "OriginMark" }],
  creator: "OriginMark",
  openGraph: {
    type: "website",
    locale: "en_US",
    url: "https://originmark.dev",
    siteName: "OriginMark",
    title: "OriginMark - Digital Signature Verification for AI Content",
    description:
      "Sign and verify AI-generated content with cryptographic signatures",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "OriginMark - AI Content Verification",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "OriginMark - AI Content Verification",
    description: "Sign and verify AI-generated content with cryptographic signatures",
    images: ["/og-image.png"],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  icons: {
    icon: "/favi.png",
    shortcut: "/favi.png",
    apple: "/favi.png",
  },
  manifest: "/site.webmanifest",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#0a0e14" },
    { media: "(prefers-color-scheme: dark)", color: "#0a0e14" },
  ],
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${outfit.variable} ${jetbrainsMono.variable}`}
      suppressHydrationWarning
    >
      <body className="min-h-screen bg-surface-950 bg-dot-grid bg-glow-orbs antialiased">
        {children}
      </body>
    </html>
  );
}