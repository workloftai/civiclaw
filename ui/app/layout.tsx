import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "civiclaw admin",
  description: "Audit log + human oversight for civiclaw skills.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
