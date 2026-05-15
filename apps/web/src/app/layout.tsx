import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "DraftLoop",
  description: "Grounded legal drafting with an improvement-from-edits loop",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        {children}
      </body>
    </html>
  );
}
