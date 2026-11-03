"use client";

import { useState, type FormEvent } from "react";

type Preview = { course: string; batch: string };

export default function ClassSetupPreview() {
  const [course, setCourse] = useState("");
  const [batch, setBatch] = useState("");
  const [error, setError] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const cleanCourse = course.trim();
    const cleanBatch = batch.trim();
    setPreview(null);
    if (!cleanCourse || !cleanBatch) {
      setError("Enter both a course name and a batch name.");
      return;
    }
    if (cleanCourse.length > 120 || cleanBatch.length > 120) {
      setError("Each name must be 120 characters or fewer.");
      return;
    }
    setError("");
    setPreview({ course: cleanCourse, batch: cleanBatch });
  }

  function clearPreview() {
    setError("");
    setPreview(null);
  }

  const courseInvalid = Boolean(error) && (!course.trim() || course.trim().length > 120);
  const batchInvalid = Boolean(error) && (!batch.trim() || batch.trim().length > 120);

  return (
    <section aria-labelledby="class-setup-title" className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
      <h2 id="class-setup-title" className="text-lg font-bold">Try class setup</h2>
      <p className="mt-2 text-sm leading-6 text-[#5C6B73]">Practice only. Nothing is saved or sent. Use example names, not children’s details.</p>
      <form onSubmit={submit} noValidate className="mt-4 space-y-4">
        <div>
          <label htmlFor="practice-course" className="block text-sm font-semibold">Course name</label>
          <input id="practice-course" aria-invalid={courseInvalid} aria-describedby={courseInvalid ? "practice-error" : undefined} value={course} maxLength={120} onChange={(event) => { setCourse(event.target.value); clearPreview(); }} className="mt-1 w-full rounded-lg border border-[#839096] px-3 py-2" />
        </div>
        <div>
          <label htmlFor="practice-batch" className="block text-sm font-semibold">Batch name</label>
          <input id="practice-batch" aria-invalid={batchInvalid} aria-describedby={batchInvalid ? "practice-error" : undefined} value={batch} maxLength={120} onChange={(event) => { setBatch(event.target.value); clearPreview(); }} className="mt-1 w-full rounded-lg border border-[#839096] px-3 py-2" />
        </div>
        {error && <p id="practice-error" role="alert" className="text-sm text-red-700">{error}</p>}
        <button type="submit" className="w-full rounded-lg bg-[#1F6F6B] px-4 py-3 font-semibold text-white">Preview class setup</button>
      </form>
      {preview && <div role="status" className="mt-4 rounded-lg bg-[#F3F5F1] p-4 text-sm"><p className="font-semibold">Preview only — not saved</p><p>Course: {preview.course}</p><p>Batch: {preview.batch}</p></div>}
    </section>
  );
}
