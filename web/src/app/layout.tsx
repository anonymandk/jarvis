import type { Metadata } from "next";
import "@fontsource-variable/space-grotesk";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";

export const metadata: Metadata = {
  title: "JARVIS | Interface de comando",
  description: "Interface direta de voz e texto para o JARVIS.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" data-theme="arc_reactor">
      <body>{children}</body>
    </html>
  );
}
