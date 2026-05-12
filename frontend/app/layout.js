import { JetBrains_Mono, Share_Tech_Mono } from "next/font/google";
import "./globals.css";

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
});

const techMono = Share_Tech_Mono({
  variable: "--font-tech-mono",
  weight: "400",
  subsets: ["latin"],
});

export const metadata = {
  title: "DEVDOCS // RAG_TERMINAL",
  description: "Local Technical Intelligence Engine",
};

export default function RootLayout({ children }) {
  return (
    <html
      lang="en"
      className={`${jetbrains.variable} ${techMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <body className="h-full bg-gray-50 text-slate-900 flex flex-col font-jetbrains">
        {children}
      </body>
    </html>
  );
}