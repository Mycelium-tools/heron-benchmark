import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const requestHeaders = await headers();
  const host = requestHeaders.get("x-forwarded-host") ?? requestHeaders.get("host") ?? "localhost:3000";
  const protocol = requestHeaders.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  const imageUrl = `${protocol}://${host}/og.png`;

  return {
    title: "HERON — Does the model give animal welfare appropriate consideration?",
    description: "A benchmark for proportionate animal-welfare consideration in ordinary requests.",
    applicationName: "HERON Benchmark",
    openGraph: {
      title: "HERON — Does the model give animal welfare appropriate consideration?",
      description: "A benchmark for proportionate animal-welfare consideration. Explore the 20-scenario pilot.",
      type: "website",
      images: [{ url: imageUrl, width: 1734, height: 907, alt: "HERON pilot leaderboard" }],
    },
    twitter: {
      card: "summary_large_image",
      title: "HERON — Does the model give animal welfare appropriate consideration?",
      description: "A benchmark for proportionate animal-welfare consideration. Explore the 20-scenario pilot.",
      images: [imageUrl],
    },
  };
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
