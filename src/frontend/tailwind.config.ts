import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        nurix: {
          navy:    "#00164A",
          navyDark:"#000e30",
          navyLight:"#002080",
          red:     "#F14468",
          redHover:"#d93358",
          gold:    "#FDB604",
          goldHover:"#e5a400",
        },
      },
    },
  },
  plugins: [],
};

export default config;
