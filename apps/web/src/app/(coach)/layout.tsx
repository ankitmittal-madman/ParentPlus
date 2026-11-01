import { BottomNavigation } from "@/ui/components/bottom-navigation";

export default function CoachLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <BottomNavigation />
    </>
  );
}
