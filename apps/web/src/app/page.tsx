import { classes, tasks } from "@/modules/dashboard/demo-data";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#F3F5F1] text-[#22303A]">
      <div className="mx-auto min-h-screen max-w-md bg-[#F3F5F1] pb-28 shadow-sm">
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

        <section className="px-5 pt-8">
          <h1 className="text-3xl font-extrabold tracking-tight">Good morning, Meera</h1>
          <p className="mt-1 text-sm text-[#5C6B73]">Here is what needs your attention today.</p>
          <div className="mt-6 grid grid-cols-3 gap-2">
            {[
              { value: "72%", label: "Fees collected", color: "bg-[#AEDEC6]" },
              { value: "91%", label: "Attendance", color: "bg-[#AFD5F0]" },
              { value: "86%", label: "Parents engaged", color: "bg-[#F2D58A]" },
            ].map((item) => (
              <div key={item.label} className={`rounded-2xl p-3 ${item.color}`}>
                <p className="text-2xl font-extrabold">{item.value}</p>
                <p className="mt-1 text-[11px] font-semibold">{item.label}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="px-5 pt-6">
          <div className="rounded-2xl bg-[#1F6F6B] p-4 text-white">
            <p className="text-xs text-white/80">Next class · 5:00 PM · Room 2</p>
            <div className="mt-1 flex items-center justify-between">
              <h2 className="text-lg font-bold">Clay Juniors</h2>
              <span className="rounded-xl bg-white px-3 py-2 text-xs font-bold text-[#1F6F6B]">Start class</span>
            </div>
          </div>
        </section>

        <section className="px-5 pt-7">
          <h2 className="mb-3 text-lg font-bold">Needs you</h2>
          <div className="overflow-hidden rounded-2xl bg-white px-4">
            {tasks.map((task, index) => (
              <div key={task.title} className={`flex items-center gap-3 py-4 ${index ? "border-t border-[#EDF1EC]" : ""}`}>
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#EDF1EC] text-lg">{task.icon}</div>
                <div className="flex-1">
                  <p className="text-sm font-bold">{task.title}</p>
                  <p className="text-xs text-[#5C6B73]">{task.detail}</p>
                </div>
                <span className="text-[#8A979D]">›</span>
              </div>
            ))}
          </div>
        </section>

        <section className="px-5 pt-7">
          <h2 className="mb-3 text-lg font-bold">Today’s classes</h2>
          <div className="overflow-hidden rounded-2xl bg-white px-4">
            {classes.map((item, index) => (
              <div key={item.name} className={`flex items-center gap-3 py-4 ${index ? "border-t border-[#EDF1EC]" : ""}`}>
                <div className="h-11 w-1 rounded-full bg-[#1F6F6B]" />
                <div className="flex-1">
                  <p className="text-sm font-bold">{item.name}</p>
                  <p className="text-xs text-[#5C6B73]">{item.time} · {item.room} · {item.children} children</p>
                </div>
                <span className="rounded-lg bg-[#EDF1EC] px-2 py-1 text-[10px] font-semibold">{item.status}</span>
              </div>
            ))}
          </div>
        </section>

        <nav aria-label="Main navigation" className="fixed bottom-3 left-1/2 grid w-[calc(100%-24px)] max-w-[408px] -translate-x-1/2 grid-cols-5 rounded-3xl border border-[#E3E8E2] bg-white p-3 shadow-lg">
          {[
            ["⌂", "Today"],
            ["▦", "Schedule"],
            ["+", "Post"],
            ["♙", "Students"],
            ["₹", "Fees"],
          ].map(([symbol, label]) => (
            <div key={label} className="flex flex-col items-center gap-1 text-[#5C6B73]">
              <span className="text-xl font-bold">{symbol}</span>
              <span className="text-[10px] font-semibold">{label}</span>
            </div>
          ))}
        </nav>
      </div>
    </main>
  );
}
