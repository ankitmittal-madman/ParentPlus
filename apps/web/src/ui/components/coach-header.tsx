import Link from "next/link";

export function CoachHeader({ academyName }: { academyName?: string }) {
  return (
        <header className="flex items-center justify-between px-5 pt-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1F6F6B] text-xl text-white">✦</div>
            <div>
              <p className="text-sm font-bold">Parent Plus Coach</p>
              {academyName && <p className="text-xs text-[#5C6B73]">{academyName}</p>}
            </div>
          </div>
          <details className="relative">
            <summary className="flex min-h-11 min-w-11 cursor-pointer list-none items-center justify-center rounded-xl bg-white text-lg shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#1F6F6B] [&::-webkit-details-marker]:hidden">
              <span className="sr-only">Open menu</span>
              <span aria-hidden="true">☰</span>
            </summary>
            <nav aria-label="Coach menu" className="absolute right-0 z-20 mt-2 w-44 rounded-xl border border-[#E3E8E2] bg-white p-2 shadow-lg">
              <Link className="block rounded-lg px-3 py-2 text-sm font-semibold hover:bg-[#E3F1EF]" href="/">Today</Link>
              <Link className="block rounded-lg px-3 py-2 text-sm font-semibold hover:bg-[#E3F1EF]" href="/schedule">Schedule</Link>
              <Link className="block rounded-lg px-3 py-2 text-sm font-semibold hover:bg-[#E3F1EF]" href="/login">Sign in</Link>
            </nav>
          </details>
        </header>
  );
}
