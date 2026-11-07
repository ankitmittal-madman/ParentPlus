import { BottomNavigation } from "@/ui/components/bottom-navigation";
import { Suspense } from "react";
import { requireCoachAccess } from "@/lib/auth/require-coach-access";

async function CoachAccessGate({ children }: { children: React.ReactNode }) {
  await requireCoachAccess();
  return <>{children}<BottomNavigation /></>;
}

export default function CoachLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<main className="mx-auto min-h-screen max-w-md bg-[#F3F5F1] px-5 py-8 text-[#22303A]">Checking coach access…</main>}>
      <CoachAccessGate>{children}</CoachAccessGate>
    </Suspense>
  );
}
