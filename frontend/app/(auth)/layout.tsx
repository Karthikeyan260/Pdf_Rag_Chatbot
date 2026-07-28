import { FileStack } from "lucide-react";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-muted/30 px-4 py-12">
      <div className="flex items-center gap-2 text-xl font-semibold">
        <FileStack className="h-6 w-6 text-primary" />
        <span>DocIntel</span>
      </div>
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}
