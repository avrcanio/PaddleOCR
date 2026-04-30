import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PaddleOCR → Searchable PDF",
  description: "Upload a file, run PaddleOCR, download searchable PDF."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

