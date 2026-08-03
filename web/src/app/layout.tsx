import type { Metadata } from "next";
import { Fraunces, Public_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Nav from "@/components/Nav";

// "Privilege Atlas" type system:
// Fraunces — high-contrast editorial serif for display.
// Public Sans — the U.S. gov / education-data sans (thematically apt) for body/UI.
// JetBrains Mono — figures, labels, codes.
const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
  style: ["normal", "italic"],
});

const sans = Public_Sans({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PIPO Index — An Atlas of American Higher Education",
  description:
    "Privilege In, Privilege Out — interactive tools charting how student privilege shapes retention, graduation, and the true cost of college.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${display.variable} ${sans.variable} ${mono.variable} h-full antialiased`}
    >
      <body className="grain flex min-h-full flex-col bg-paper text-ink">
        <Nav />
        <main className="flex-1">{children}</main>
        <footer className="border-t border-rule">
          <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-6 py-10 sm:flex-row sm:items-end sm:justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="dot-in" aria-hidden />
                <span className="dot-out" aria-hidden />
                <span className="font-display text-lg font-semibold tracking-tight">
                  PIPO&nbsp;Index
                </span>
              </div>
              <p className="max-w-sm text-sm text-ink-soft">
                An independent atlas of American higher education. Privilege in,
                privilege out.
              </p>
            </div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-ink-soft">
              Sources · IPEDS · College&nbsp;Scorecard · US&nbsp;News
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
