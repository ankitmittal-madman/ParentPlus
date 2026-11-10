"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { NavigationIcon } from "./navigation-icon";

const items = [
  { href: "/", label: "Today", icon: "home" },
  { href: "/schedule", label: "Schedule", icon: "calendar" },
  { href: "/post", label: "Post", icon: "plus" },
  { href: "/students", label: "Students", icon: "students" },
  { href: "/fees", label: "Fees", icon: "wallet" },
] as const;

export function BottomNavigation() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Main navigation"
      className="fixed bottom-[max(12px,env(safe-area-inset-bottom))] left-1/2 z-50 grid w-[calc(100%-24px)] max-w-[408px] -translate-x-1/2 grid-cols-5 rounded-3xl border border-[#E3E8E2] bg-white p-3 shadow-lg"
    >
      {items.map((item) => {
        const active = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-11 flex-col items-center justify-center gap-1 rounded-xl ${
              active ? "bg-[#E3F1EF] text-[#1F6F6B]" : "text-[#5C6B73]"
            }`}
          >
            <span
              className={
                item.href === "/post"
                  ? "-mt-7 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#1F6F6B] text-white shadow-lg"
                  : "flex h-7 items-center justify-center"
              }
            >
              <NavigationIcon name={item.icon} />
            </span>
            <span className="text-[10px] font-semibold">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
