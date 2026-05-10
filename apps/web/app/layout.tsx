import type { Metadata } from "next";
import type { ReactNode } from "react";
import { AuthProvider } from "../components/providers/AuthProvider";
import { QueryProvider } from "../components/providers/QueryProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "Campaign Map Forge",
  description: "A browser-based D&D campaign map editor"
};

export default function RootLayout({
  children
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <QueryProvider>
          <AuthProvider>{children}</AuthProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
