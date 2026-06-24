import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ongp: {
          ink: "#17211f",
          green: "#176b55",
          gold: "#d9a441",
          paper: "#f7f6f1",
        },
      },
    },
  },
  plugins: [],
};

export default config;
