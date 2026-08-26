import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Space_Grotesk } from "next/font/google";
import NavBar from "./NavBar";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["500", "600", "700"],
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
      <html lang="pt-BR" className={spaceGrotesk.variable}>
        <body className="bg-[#F6F7F5] text-[#14181F] antialiased">
          <NavBar />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}