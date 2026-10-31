import { CoachHeader } from "@/ui/components/coach-header";
import { DashboardStats } from "@/ui/components/dashboard-stats";
import { classes, tasks } from "@/modules/dashboard/demo-data";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#F3F5F1] text-[#22303A]">
      <div className="mx-auto min-h-screen max-w-md bg-[#F3F5F1] pb-28 shadow-sm">
        <CoachHeader />

        <section className="px-5 pt-8">
          <h1 className="text-3xl font-extrabold tracking-tight">Good morning, Meera</h1>
          <p className="mt-1 text-sm text-[#5C6B73]">Here is what needs your attention today.</p>
          <DashboardStats />
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


      </div>
    </main>
  );
}
