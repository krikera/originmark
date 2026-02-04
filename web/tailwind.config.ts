import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    darkMode: "class",
    theme: {
        extend: {
            colors: {
                // Deep Teal - Premium trust palette
                primary: {
                    50: "#f0fafa",
                    100: "#dcf0f0",
                    200: "#bce3e3",
                    300: "#8dcfcf",
                    400: "#4db3b3",
                    500: "#00B3A4", // mint-teal accent
                    600: "#008a7f",
                    700: "#005F60", // deep teal main
                    800: "#004a4b",
                    900: "#003d3e",
                    950: "#002728",
                },
                // Mint Teal - Interactive accent
                accent: {
                    50: "#f0fafa",
                    100: "#d9f5f3",
                    200: "#b3ebe7",
                    300: "#80dcd5",
                    400: "#4dc5bd",
                    500: "#00B3A4", // mint-teal
                    600: "#009187",
                    700: "#00756d",
                    800: "#005e57",
                    900: "#004d48",
                },
                // Platinum surface colors
                surface: {
                    50: "#F7FAFA", // platinum background
                    100: "#DCEEEE", // border
                    200: "#c5e3e3",
                    300: "#a8d5d5",
                    400: "#7ab9b9",
                    500: "#5aa5a5",
                    600: "#458585",
                    700: "#1C2B2D", // text
                    800: "#162022",
                    900: "#0f1819",
                    950: "#090f10",
                },
            },
            fontFamily: {
                sans: ["var(--font-inter)", "system-ui", "sans-serif"],
                display: ["var(--font-outfit)", "system-ui", "sans-serif"],
                mono: ["var(--font-jetbrains)", "monospace"],
            },
            backgroundImage: {
                "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
                "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
                "mesh-gradient": "url('/mesh-gradient.svg')",
                "hero-gradient": "linear-gradient(135deg, #00B3A4 0%, #005F60 50%, #004a4b 100%)",
                "card-gradient": "linear-gradient(145deg, rgba(0, 179, 164, 0.1) 0%, rgba(0, 179, 164, 0.05) 100%)",
            },
            boxShadow: {
                "glow": "0 0 40px rgba(0, 179, 164, 0.25)",
                "glow-lg": "0 0 60px rgba(0, 179, 164, 0.35)",
                "glow-accent": "0 0 40px rgba(0, 179, 164, 0.3)",
                "inner-glow": "inset 0 0 20px rgba(0, 95, 96, 0.1)",
                "glass": "0 8px 32px rgba(0, 0, 0, 0.12)",
                "glass-lg": "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
            },
            animation: {
                "fade-in": "fadeIn 0.5s ease-out forwards",
                "slide-up": "slideUp 0.5s ease-out forwards",
                "slide-down": "slideDown 0.3s ease-out forwards",
                "scale-in": "scaleIn 0.3s ease-out forwards",
                "pulse-glow": "pulseGlow 2s ease-in-out infinite",
                "float": "float 6s ease-in-out infinite",
                "shimmer": "shimmer 2s linear infinite",
            },
            keyframes: {
                fadeIn: {
                    "0%": { opacity: "0" },
                    "100%": { opacity: "1" },
                },
                slideUp: {
                    "0%": { opacity: "0", transform: "translateY(20px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                slideDown: {
                    "0%": { opacity: "0", transform: "translateY(-10px)" },
                    "100%": { opacity: "1", transform: "translateY(0)" },
                },
                scaleIn: {
                    "0%": { opacity: "0", transform: "scale(0.95)" },
                    "100%": { opacity: "1", transform: "scale(1)" },
                },
                pulseGlow: {
                    "0%, 100%": { boxShadow: "0 0 20px rgba(0, 179, 164, 0.25)" },
                    "50%": { boxShadow: "0 0 40px rgba(0, 179, 164, 0.5)" },
                },
                float: {
                    "0%, 100%": { transform: "translateY(0)" },
                    "50%": { transform: "translateY(-10px)" },
                },
                shimmer: {
                    "0%": { backgroundPosition: "-200% 0" },
                    "100%": { backgroundPosition: "200% 0" },
                },
            },
            backdropBlur: {
                xs: "2px",
            },
        },
    },
    plugins: [],
};

export default config;
