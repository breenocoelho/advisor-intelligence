import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Space_Grotesk, Space_Mono, Inter } from "next/font/google";
import NavBar from "./NavBar";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  weight: ["400", "500", "600"],
});

const spaceMono = Space_Mono({
  subsets: ["latin"],
  variable: "--font-number",
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "Advisor Intelligence",
  description: "Painel de prioridades do assessor",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html
        lang="pt-BR"
        className={`${spaceGrotesk.variable} ${inter.variable} ${spaceMono.variable}`}
      >
        <body className="antialiased">
          <NavBar />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}