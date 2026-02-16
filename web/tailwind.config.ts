import type { Config } from "tailwindcss";

const config: Config = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./components/**/*.{js,ts,jsx,tsx,mdx}",
        "./app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
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
                    500: "#00B3A4",
                    600: "#008a7f",
                    700: "#005F60",
                    800: "#004a4b",
                    900: "#003d3e",
                    950: "#002728",
                },
                // Bright Cyan accent
                accent: {
                    50: "#ecfefb",
                    100: "#d1faf5",
                    200: "#a8f4ec",
                    300: "#6eebe0",
                    400: "#33dccf",
                    500: "#00D9C5",
                    600: "#00b3a4",
                    700: "#008f84",
                    800: "#00726a",
                    900: "#005d57",
                },
                // Dark surface palette
                surface: {
                    50: "#f0f4f8",
                    100: "#d9e2ec",
                    200: "#bcccdc",
                    300: "#9fb3c8",
                    400: "#829ab1",
                    500: "#627d98",
                    600: "#486581",
                    700: "#334e68",
                    800: "#1a2332",
                    900: "#0f1722",
                    950: "#0a0e14",
                },
            },
            fontFamily: {
                sans: ["var(--font-inter)", "system-ui", "sans-serif"],
                display: ["var(--font-outfit)", "system-ui", "sans-serif"],
                mono: ["var(--font-jetbrains)", "monospace"],
            },
            backgroundImage: {
                "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
                "hero-gradient": "linear-gradient(135deg, #00D9C5 0%, #005F60 50%, #003d3e 100%)",
            },
            boxShadow: {
                "glow": "0 0 40px rgba(0, 217, 197, 0.25)",
                "glow-lg": "0 0 60px rgba(0, 217, 197, 0.35)",
                "glow-accent": "0 0 40px rgba(0, 217, 197, 0.3)",
                "inner-glow": "inset 0 0 20px rgba(0, 95, 96, 0.1)",
            },
            animation: {
                "fade-in": "fadeIn 0.5s ease-out forwards",
                "slide-up": "slideUp 0.5s ease-out forwards",
                "slide-down": "slideDown 0.3s ease-out forwards",
                "scale-in": "scaleIn 0.3s ease-out forwards",
                "pulse-glow": "pulseGlow 3s ease-in-out infinite",
                "float": "float 6s ease-in-out infinite",
                "breathe": "breathe 4s ease-in-out infinite",
                "typing-cursor": "typing-cursor 1s step-end infinite",
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
                    "0%, 100%": { boxShadow: "0 0 20px rgba(0, 217, 197, 0.2)" },
                    "50%": { boxShadow: "0 0 48px rgba(0, 217, 197, 0.5)" },
                },
                float: {
                    "0%, 100%": { transform: "translateY(0)" },
                    "50%": { transform: "translateY(-12px)" },
                },
                breathe: {
                    "0%, 100%": { opacity: "0.4", transform: "scale(1)" },
                    "50%": { opacity: "0.8", transform: "scale(1.05)" },
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
