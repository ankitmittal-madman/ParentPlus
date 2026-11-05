import ClassSetupPreview from "./class-setup-preview";
import { Suspense } from "react";
import ClassRecoveryGate from "./class-recovery-gate";

const exampleSessions = [
  { course: "Clay Basics", batch: "Clay Juniors", time: "Example Monday, 5:00 PM" },
  { course: "Colour and Painting", batch: "Colour Explorers", time: "Example Wednesday, 4:00 PM" },
];

export default function Page() {
  return (
    <main className="mx-auto min-h-screen max-w-md bg-[#F3F5F1] px-5 pb-28 pt-8 text-[#22303A]">
      <p className="text-sm font-semibold text-[#1F6F6B]">Parent Plus Coach</p>
      <h1 className="mt-6 text-3xl font-extrabold">Schedule</h1>
      <ClassSetupPreview />
      <Suspense fallback={null}><ClassRecoveryGate /></Suspense>
      <section aria-labelledby="example-sessions" className="mt-8">
        <h2 id="example-sessions" className="text-lg font-bold">Example sessions</h2>
      <p className="mt-3 text-sm leading-6 text-[#5C6B73]">
        Example data only — these are not real classes or bookings.
      </p>

        <ul aria-label="Example sessions" className="mt-4 space-y-4">
          {exampleSessions.map((session) => (
            <li key={session.batch} className="rounded-2xl bg-white p-5 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-[#1F6F6B]">Course</p>
              <p className="mt-1 font-bold">{session.course}</p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-[#5C6B73]">Batch</p>
              <p className="mt-1 text-sm">{session.batch}</p>
              <p className="mt-3 text-sm font-semibold">{session.time}</p>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
