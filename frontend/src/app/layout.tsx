import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ActionFlow — Plan • Orchestrate • Act",
  description: "ActionFlow is an agentic assistant that understands your goals, breaks them into tasks, selects tools, and executes multi-step workflows with confirmation controls. Powered by Amazon Bedrock and a self-hosted MCP server.",
  keywords: ["ActionFlow", "Agentic AI", "Amazon Bedrock", "MCP", "Alexa+", "AWS"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
