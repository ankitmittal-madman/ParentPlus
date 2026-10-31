"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Today", icon: "⌂" },
  { href: "/schedule", label: "Schedule", icon: "▦" },
  { href: "/post", label: "Post", icon: "+" },
  { href: "/students", label: "Students", icon: "♙" },
  { href: "/fees", label: "Fees", icon: "₹" },
];

export function BottomNavigation() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Main navigation"
      className="fixed bottom-3 left-1/2 z-50 grid w-[calc(100%-24px)] max-w-[408px] -translate-x-1/2 grid-cols-5 rounded-3xl border border-[#E3E8E2] bg-white p-3 shadow-lg"
    >
      {items.map((item) => {
        const active = pathname === item.href;

        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={`flex min-h-11 flex-col items-center justify-center gap-1 rounded-xl ${
              active
                ? "bg-[#E3F1EF] text-[#1F6F6B]"
                : "text-[#5C6B73]"
            }`}
          >
            <span aria-hidden="true" className="text-xl font-bold">
              {item.icon}
            </span>
            <span className="text-[10px] font-semibold">
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
