import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "FitAgent - 智能健身助手",
  description: "企业级任务型健身 Agent，用自然语言管理你的训练",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="zh-CN" className="h-full">
      <body className="h-full antialiased bg-gray-50 text-gray-900">
        {children}
      </body>
    </html>
  )
}
