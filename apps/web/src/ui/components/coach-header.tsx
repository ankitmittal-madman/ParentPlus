export function CoachHeader() {
  return (
        <header className="flex items-center justify-between px-5 pt-7">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#1F6F6B] text-xl text-white">✦</div>
            <div>
              <p className="text-sm font-bold">Parent Plus Coach</p>
              <p className="text-xs text-[#5C6B73]">The Creative Room</p>
            </div>
          </div>
          <div className="rounded-xl bg-white px-3 py-2 text-lg shadow-sm">☰</div>
        </header>
  );
}
