import { test, expect, login, emailFor, workspace, child, setup } from "./fixtures";
import type { Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { createServerClient } from "@supabase/ssr";
const BATCH="QA Attendance Juniors", CHILD="Fictional Attendance Child";
async function signOut(page: Page) {
  await page.goto("/login");
  await page.getByRole("button",{name:"Sign out",exact:true}).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
}
async function prepare(page: Page, timeZone = "Asia/Kolkata", existingParent?: string) {
  const coach=emailFor(); await login(page,coach);
  const academy=await workspace(page,"academy");
  const today=new Intl.DateTimeFormat("en-CA",{timeZone,year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
  const p=await setup(page);
  await p.getByLabel("Course name",{exact:true}).fill("QA Attendance Clay");
  await p.getByLabel("Batch name",{exact:true}).fill(BATCH);
  await p.getByLabel("Academy time zone",{exact:true}).fill(timeZone);
  await p.getByLabel("First session date").fill(today);
  await p.getByLabel("Local start time").fill("17:00");
  await p.getByLabel("Last date for weekly sessions").fill(today);
  await p.getByRole("button",{name:"Create course, batch and weekly sessions",exact:true}).click();
  await expect(p.getByText("Weekly schedule: 1 sessions",{exact:true})).toBeVisible();
  await p.getByRole("button",{name:"Confirm course, batch and schedule",exact:true}).click();
  await expect(p.getByText("Setup completed — acknowledged",{exact:true})).toBeVisible();
  await page.goto("/students");
  await page.getByRole("button",{name:"Load academies",exact:true}).click();
  await page.getByLabel("Academy",{exact:true}).selectOption({label:academy});
  await page.getByRole("button",{name:"Add a student",exact:true}).click();
  const invite=await page.getByLabel("Family invite link").inputValue();
  await signOut(page); const parent=await login(page,existingParent); if (!existingParent) await child(page,CHILD);
  await page.goto(invite);
  await page.getByRole("button",{name:"Check invitation",exact:true}).click();
  await page.getByLabel("Your child",{exact:true}).selectOption({label:CHILD});
  await page.getByLabel(/I confirm this is my child/).check();
  await page.getByRole("button",{name:"Confirm academy connection",exact:true}).click();
  await expect(page.getByText("Connection saved. Batch enrolment is a separate step.",{exact:true})).toBeVisible();
  await signOut(page); await login(page,coach); await page.goto("/students");
  const enrol=page.getByRole("region",{name:"Batch enrolment",exact:true});
  await enrol.getByRole("button",{name:BATCH,exact:true}).click();
  await enrol.getByLabel("Connected child",{exact:true}).selectOption({label:CHILD});
  await enrol.getByRole("button",{name:"Enrol child",exact:true}).click();
  await expect(enrol.getByRole("article").filter({hasText:CHILD}).getByText("Active",{exact:true})).toBeVisible();
  await page.goto("/");
  await expect(page.getByLabel("Session date",{exact:true})).toHaveValue(today);
  await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
  const sheet=page.getByRole("region",{name:"Attendance",exact:true});
  await expect(sheet.getByText(CHILD,{exact:true})).toBeVisible();
  return {sheet,coach,parent,academy,today};
}

test("[ATTEND-001] real dated roster saves explicit marks and reloads confirmed attendance",async({page})=>{
  test.setTimeout(150_000);
  const {sheet,today}=await prepare(page);
  await test.step("Opening attendance leaves the child unmarked until the coach acts",async()=>{
    await expect(sheet.getByText("Unmarked",{exact:true})).toBeVisible();
    await expect(sheet.getByRole("button",{name:"Save attendance",exact:true})).toBeDisabled();
    await sheet.getByRole("button",{name:`Absent for ${CHILD}`,exact:true}).click();
    await sheet.getByRole("button",{name:"Mark all present",exact:true}).click();
    await expect(sheet.getByRole("button",{name:`Absent for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
  });
  await test.step("Enabled Save and selected date and mark have distinct rendered colours",async()=>{
    const save=sheet.getByRole("button",{name:"Save attendance",exact:true});
    await expect(save).toBeEnabled();
    await save.scrollIntoViewIfNeeded();
    await expect(save).toBeInViewport();
    await expect(save).toHaveCSS("background-color","rgb(31, 111, 107)");
    await expect(save).toHaveCSS("color","rgb(255, 255, 255)");
    await expect(save).toHaveCSS("opacity","1");
    const contrast=await save.evaluate(element=>{
      const style=getComputedStyle(element);
      const luminance=(colour:string)=>{
        const channels=colour.match(/\d+(?:\.\d+)?/g)!.slice(0,3).map(Number).map(value=>value/255).map(value=>value<=0.04045?value/12.92:((value+0.055)/1.055)**2.4);
        return channels[0]*0.2126+channels[1]*0.7152+channels[2]*0.0722;
      };
      const foreground=luminance(style.color),background=luminance(style.backgroundColor);
      return (Math.max(foreground,background)+0.05)/(Math.min(foreground,background)+0.05);
    });
    expect(contrast).toBeGreaterThanOrEqual(4.5);
    await expect(sheet.getByRole("button",{name:`Absent for ${CHILD}`,exact:true})).toHaveCSS("background-color","rgb(217, 238, 234)");
    await expect(sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true})).toHaveCSS("background-color","rgb(255, 255, 255)");
    await expect(page.getByRole("button",{name:`Select session date ${today}`,exact:true})).toHaveCSS("background-color","rgb(217, 238, 234)");
    const screenshot=test.info().outputPath("enabled-attendance-controls.png");
    await page.screenshot({path:screenshot,fullPage:true});
    await test.info().attach("enabled-attendance-controls",{path:screenshot,contentType:"image/png"});
  });
  await test.step("Save and reload preserve the actual database result",async()=>{
    await sheet.getByRole("button",{name:`Late for ${CHILD}`,exact:true}).click();
    await sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
    await expect(sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
    await page.reload();
    await expect(page.getByLabel("Session date",{exact:true})).toHaveValue(today);
    await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
    await expect(sheet.getByRole("button",{name:`Late for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
    await sheet.getByRole("button",{name:"Refresh attendance",exact:true}).click();
    await expect(sheet.getByRole("button",{name:`Late for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
  });
  await test.step("Reviewing empty parent reports and changing the date do not replace saved marks",async()=>{
    await sheet.getByRole("button",{name:"Review parent signals",exact:true}).click();
    await expect(sheet.getByText("No parent reports on this page.",{exact:true})).toBeVisible();
    await sheet.getByRole("button",{name:"Apply absent suggestions",exact:true}).click();
    await expect(sheet.getByRole("button",{name:`Late for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
    await sheet.getByRole("button",{name:"Review parent signals",exact:true}).click();
    await page.getByRole("button",{name:`Select session date ${today}`,exact:true}).click();
    await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
    await expect(sheet.getByRole("button",{name:`Late for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
  });
  await test.step("All five attendance marks are explicit and persist as corrections",async()=>{
    for (const label of ["Present","Absent","Excused","Make-up"]) {
      if (["Excused","Make-up"].includes(label)) {
        const summary=sheet.locator("summary",{hasText:"More"});
        // Native summary is a button-like control, retained for keyboard access.
        if (!await summary.evaluate(element=>element.parentElement!.hasAttribute("open"))) await summary.click();
      }
      await sheet.getByRole("button",{name:`${label} for ${CHILD}`,exact:true}).click();
      await sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
      await expect(sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
      await expect(sheet.getByRole("button",{name:`${label} for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
    }
    await page.getByRole("button",{name:"Refresh Today",exact:true}).click();
    await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
    await sheet.locator("summary").click();
    await expect(sheet.getByRole("button",{name:`Make-up for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
  });
});

test("[ATTEND-003] unconfirmed uncommitted save checks unknown then retries the same operation",async({page})=>{
  test.setTimeout(150_000);
  const {sheet}=await prepare(page);
  await sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true}).click();
  let dropped=false;
  await page.route("http://127.0.0.1:3193/",async route=>{
    if (!dropped && route.request().method()==="POST" && (route.request().postData()||"").includes('"operation":"save_attendance"')) {
      dropped=true; await route.abort();
    } else await route.fallback();
  });
  const pending=()=>page.evaluate(()=>Object.entries(sessionStorage).find(([key])=>key.startsWith("parentplus:attendance-pending:"))?.[1]||null);
  await sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
  await expect(sheet.getByText("Save result is unconfirmed. Check the saved result or retry the same request.",{exact:true})).toBeVisible();
  expect(dropped).toBe(true);
  const original=await pending(); expect(original).not.toBeNull();
  await sheet.getByRole("button",{name:"Check saved result",exact:true}).click();
  await expect(sheet.getByRole("button",{name:"Retry same request",exact:true})).toBeEnabled();
  expect(await pending()).toBe(original);
  await sheet.getByRole("button",{name:"Retry same request",exact:true}).click();
  await expect(sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
  expect(await pending()).toBeNull();
  await page.reload();
  await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
  await expect(sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
});

test("[ATTEND-002] committed save with lost response recovers the original request after reload",async({page})=>{
  test.setTimeout(150_000);
  const {sheet}=await prepare(page);
  await sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true}).click();
  let committed=false;
  await page.route("http://127.0.0.1:3193/",async route=>{
    const request=route.request();
    if (!committed && request.method()==="POST" && (request.postData()||"").includes('"operation":"save_attendance"')) {
      const response=await route.fetch();
      expect(response.ok()).toBe(true);
      committed=true;
      await route.abort();
    } else await route.fallback();
  });
  await sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
  await expect(sheet.getByText("Save result is unconfirmed. Check the saved result or retry the same request.",{exact:true})).toBeVisible();
  expect(committed).toBe(true);
  const pending=await page.evaluate(()=>{
    const key=Object.keys(sessionStorage).find(key=>key.startsWith("parentplus:attendance-pending:"));
    return key ? JSON.parse(sessionStorage.getItem(key)!) : null;
  });
  expect(pending?.payload.operation).toBe("save_attendance");
  const ids=[pending.requestId,pending.payload.session_id];
  for (const id of ids) expect(id).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  const persisted=()=>execFileSync("docker",["--host=unix:///var/run/docker.sock","exec","supabase_db_ParentPlus","psql","-XAt","-v","ON_ERROR_STOP=1","-U","postgres","-d","postgres","-c",`select (select count(*) from public.attendance_request_receipts where request_id='${ids[0]}'),(select count(*) from public.attendance_record_events where session_id='${ids[1]}'),(select count(*) from public.parent_items where source_session_id='${ids[1]}'),(select version from public.attendance_sheets where session_id='${ids[1]}');`],{encoding:"utf8"}).trim();
  expect(persisted()).toBe("1|1|1|1");
  await page.reload();
  await page.getByRole("button",{name:"Check saved result",exact:true}).click();
  await expect(page.getByText("Attendance saved.",{exact:true})).toBeVisible();
  await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
  await expect(sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true})).toHaveAttribute("aria-pressed","true");
  expect(persisted()).toBe("1|1|1|1");
  expect(await page.evaluate(()=>Object.keys(sessionStorage).some(key=>key.startsWith("parentplus:attendance-pending:")))).toBe(false);
});

test("[PARENTATTEND-001] saved attendance and reports stay scoped to the child through correction and pause",async({page})=>{
  test.setTimeout(210_000);
  // Actual academy UTC day avoids an India-midnight boundary during this long journey.
  const {sheet,coach,parent,academy,today}=await prepare(page,"UTC");
  await sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true}).click();
  await sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
  await expect(sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
  await signOut(page); await login(page,parent);
  await page.getByRole("link",{name:"Parent home",exact:true}).click();
  const sessions=page.getByRole("region",{name:"Sessions",exact:true});
  const feed=page.getByRole("region",{name:"Saved updates",exact:true});
  const week=page.getByRole("region",{name:"This week",exact:true});
  const oneRecorded=async()=>{
    await expect(week.locator("p").filter({hasText:"Attended this week"}).locator("strong")).toHaveText("1");
    await expect(week.locator("p").filter({hasText:"Saved attendance records"}).locator("span")).toHaveText("1");
    await expect(feed.getByRole("article")).toHaveCount(1);
  };
  await test.step("Parent loads own child, academy, class, saved attendance and exact weekly facts",async()=>{
    await expect(page.getByRole("heading",{name:"Parent home",exact:true})).toBeVisible();
    await expect(page.getByLabel("Child",{exact:true}).getByRole("option",{name:CHILD,exact:true})).toHaveCount(1);
    await expect(page.getByLabel("Academy",{exact:true}).getByRole("option",{name:academy,exact:true})).toHaveCount(1);
    await expect(page.getByLabel("Session date",{exact:true})).toHaveValue(today);
    await page.getByLabel("Class",{exact:true}).selectOption({label:`${BATCH} · QA Attendance Clay`});
    await expect(sessions.getByText("Coach confirmed: Present",{exact:true})).toBeVisible();
    await expect(feed.getByText("Present",{exact:true})).toBeVisible();
    await oneRecorded(); await page.reload();
    await expect(feed.getByText("Present",{exact:true})).toBeVisible(); await oneRecorded();
    await page.getByRole("navigation",{name:"Parent home",exact:true}).getByRole("link",{name:"Home",exact:true}).click();
    await page.getByRole("link",{name:"Profiles and connections",exact:true}).click();
    await expect(page).toHaveURL(/\/parent\/children$/);
    await page.getByRole("link",{name:"Parent home",exact:true}).click();
    await expect(feed.getByText("Present",{exact:true})).toBeVisible();
    const tomorrow=new Date(`${today}T12:00:00Z`);tomorrow.setUTCDate(tomorrow.getUTCDate()+1);
    await page.getByLabel("Session date",{exact:true}).fill(tomorrow.toISOString().slice(0,10));
    await expect(sessions.getByText("No sessions on this date.",{exact:true})).toBeVisible();
    await page.getByLabel("Session date",{exact:true}).fill(today);
    await page.locator('button[data-qa-action="Select parent session date"][aria-pressed="true"]').click();
    await expect(sessions.getByText("Coach confirmed: Present",{exact:true})).toBeVisible();
  });
  const targetChild=await page.getByLabel("Child",{exact:true}).inputValue();
  const targetWorkspace=await page.getByLabel("Academy",{exact:true}).inputValue();
  await test.step("Four parent report types persist while attendance and counts remain coach-confirmed",async()=>{
    for(const label of ["Running late","Missing today","Dropped off","Picked up"]){
      await sessions.getByRole("button",{name:new RegExp(`^Send parent report for ${BATCH} `)}).click();
      const report=page.getByRole("region",{name:"Parent report",exact:true});
      await report.getByRole("button",{name:label,exact:true}).click();
      if(label==="Missing today"){
        await expect(report.getByRole("button",{name:"Send report",exact:true})).toBeDisabled();
        await report.getByLabel("Missing reason",{exact:true}).selectOption("unwell");
      }
      await report.getByRole("button",{name:"Send report",exact:true}).click();
      await expect(report).toHaveCount(0);
      await expect(sessions.getByText(new RegExp(`Parent report: ${label}`))).toBeVisible();
      await expect(sessions.getByText("Coach confirmed: Present",{exact:true})).toBeVisible(); await oneRecorded();
    }
    await page.getByRole("button",{name:"Refresh parent home",exact:true}).click();
    await expect(sessions.getByText(/Parent report: Picked up/)).toBeVisible(); await oneRecorded();
  });
  await test.step("Coach sees the correct session report; a correction updates one existing parent item",async()=>{
    await signOut(page);await login(page,coach);await page.goto("/");
    await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
    await sheet.getByRole("button",{name:"Review parent signals",exact:true}).click();
    await expect(sheet.getByText(/Parent report: Picked up/)).toBeVisible();
    await sheet.getByRole("button",{name:`Late for ${CHILD}`,exact:true}).click();
    await sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
    await expect(sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
    await signOut(page);await login(page,parent);await page.goto("/parent");
    await expect(feed.getByText("Late",{exact:true})).toBeVisible();await oneRecorded();
  });
  await test.step("Pause removes the active coach roster and report eligibility but retains parent history",async()=>{
    await signOut(page);await login(page,coach);await page.goto("/students");
    const enrol=page.getByRole("region",{name:"Batch enrolment",exact:true});
    await enrol.getByRole("button",{name:BATCH,exact:true}).click();
    const row=enrol.getByRole("article").filter({hasText:CHILD});
    await row.getByLabel("Reason",{exact:true}).selectOption("temporary_break");
    await row.getByRole("button",{name:"Pause enrolment",exact:true}).click();
    await expect(row.getByText("Paused",{exact:true})).toBeVisible();
    await page.goto("/");await page.getByRole("button",{name:`Open attendance for ${BATCH}`,exact:true}).click();
    await expect(sheet.getByText("No enrolled children in this session. Attendance cannot be saved.",{exact:true})).toBeVisible();
    await expect(sheet.getByRole("button",{name:"Save attendance",exact:true})).toBeDisabled();
    await signOut(page);await login(page,parent);await page.goto("/parent");
    await expect(sessions.getByText("Paused enrolment",{exact:true})).toBeVisible();
    await expect(sessions.getByRole("button",{name:/^Send parent report for /})).toHaveCount(0);
    await expect(feed.getByText("Late",{exact:true})).toBeVisible();await oneRecorded();
  });
  await test.step("A different signed parent is denied by the actual private RPC, not only by hidden UI",async()=>{
    await signOut(page);const stranger=await login(page);await child(page,"Fictional Unrelated Attendance Child");
    await page.goto(`/parent?child=${targetChild}`);
    await expect(page.getByText("No eligible academy connections for this child.",{exact:true})).toBeVisible();
    await expect(page.getByText(CHILD,{exact:true})).toHaveCount(0);
    const key=readFileSync("../../work/local-supabase.env","utf8").match(/^ANON_KEY=(.*)$/m)?.[1].trim().replace(/^["']|["']$/g,"");
    if(!key)throw new Error("Local public browser key is unavailable");
    const cookies=await page.context().cookies();
    const client=createServerClient("http://127.0.0.1:54321",key,{cookies:{getAll:()=>cookies.map(({name,value})=>({name,value})),setAll:()=>{}}});
    const identity=await client.auth.getUser();expect(identity.error).toBeNull();expect(identity.data.user?.email).toBe(stranger);
    const denied=await client.rpc("app_parent_items",{p_child_id:targetChild,p_workspace_id:targetWorkspace,p_batch_id:null,p_before_created:null,p_before_id:null});
    expect(denied.error?.code).toBe("42501");expect(denied.data).toBeNull();
    await signOut(page);await login(page,parent);await page.goto("/parent");
    await expect(feed.getByText("Late",{exact:true})).toBeVisible();await oneRecorded();
  });
  await test.step("Hindi copy preserves actual saved facts and English can be restored",async()=>{
    const language=page.getByRole("combobox",{name:"Page language / पृष्ठ की भाषा",exact:true});
    await language.selectOption("hi");
    await expect(page.getByRole("heading",{name:"अभिभावक होम",exact:true})).toBeVisible();
    const hindiFeed=page.getByRole("region",{name:"सहेजे अपडेट",exact:true});
    await expect(hindiFeed.getByText("देर से",{exact:true})).toBeVisible();
    await page.getByRole("button",{name:"अभिभावक होम रीफ़्रेश करें",exact:true}).click();
    await expect(hindiFeed.getByText("देर से",{exact:true})).toBeVisible();
    await page.getByRole("navigation",{name:"अभिभावक होम",exact:true}).getByRole("link",{name:"होम",exact:true}).click();
    await page.getByRole("link",{name:"प्रोफ़ाइल और कनेक्शन",exact:true}).click();
    await expect(page).toHaveURL(/\/parent\/children$/);
    await page.getByRole("link",{name:"Parent home",exact:true}).click();
    await expect(hindiFeed.getByText("देर से",{exact:true})).toBeVisible();
    const screenshot=test.info().outputPath("parent-home-hindi.png");
    await page.screenshot({path:screenshot,fullPage:true});await test.info().attach("parent-home-hindi",{path:screenshot,contentType:"image/png"});
    await language.selectOption("en");await expect(feed.getByText("Late",{exact:true})).toBeVisible();await oneRecorded();
  });
});

for (const committed of [false, true]) {
  const scenario = committed ? "PARENTATTEND-002" : "PARENTATTEND-003";
  test(`[${scenario}] ${committed ? "committed report with lost response resolves after reload" : "uncommitted report checks unknown then retries the original request"}`,async({page})=>{
    test.setTimeout(180_000);
    const {parent}=await prepare(page,"UTC");
    await signOut(page);await login(page,parent);await page.goto("/parent");
    const sessions=page.getByRole("region",{name:"Sessions",exact:true});
    await sessions.getByRole("button",{name:/^Send parent report for /}).click();
    const report=page.getByRole("region",{name:"Parent report",exact:true});
    let dropped=false;
    await page.route("http://127.0.0.1:3193/parent",async route=>{
      if(!dropped && route.request().method()==="POST" && (route.request().postData()||"").includes('"operation":"send_parent_signal"')){
        if(committed){const response=await route.fetch();expect(response.ok()).toBe(true);}
        dropped=true;await route.abort();
      }else await route.fallback();
    });
    await report.getByRole("button",{name:"Send report",exact:true}).click();
    await expect(report.getByText("Report result is unconfirmed. Check the result or retry the same request before sending another report.",{exact:true})).toBeVisible();
    expect(dropped).toBe(true);
    const pending=()=>page.evaluate(()=>Object.entries(sessionStorage).find(([key])=>key.startsWith("parentplus:signal-pending:"))?.[1]||null);
    const original=await pending();expect(original).not.toBeNull();
    const operation=JSON.parse(original!);
    expect(operation.payload.operation).toBe("send_parent_signal");
    for(const value of [operation.requestId,operation.payload.session_id])expect(value).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
    const rows=()=>execFileSync("docker",["--host=unix:///var/run/docker.sock","exec","supabase_db_ParentPlus","psql","-XAt","-v","ON_ERROR_STOP=1","-U","postgres","-d","postgres","-c",`select (select count(*) from public.parent_signal_request_receipts where request_id='${operation.requestId}'),(select count(*) from public.parent_signals where session_id='${operation.payload.session_id}'),(select count(*) from public.attendance_records where session_id='${operation.payload.session_id}'),(select count(*) from public.parent_items where source_session_id='${operation.payload.session_id}');`],{encoding:"utf8"}).trim();
    expect(rows()).toBe(committed?"1|1|0|0":"0|0|0|0");
    if(committed){await page.reload();expect(await pending()).toBe(original);}
    await report.getByRole("button",{name:"Check report result",exact:true}).click();
    if(!committed){
      await expect(report.getByRole("button",{name:"Retry same report",exact:true})).toBeEnabled();
      expect(await pending()).toBe(original);expect(rows()).toBe("0|0|0|0");
      await report.getByRole("button",{name:"Retry same report",exact:true}).click();
    }
    await expect(report).toHaveCount(0);
    await expect(sessions.getByText(/Parent report: Running late/)).toBeVisible();
    expect(await pending()).toBeNull();expect(rows()).toBe("1|1|0|0");
    await page.reload();
    await expect(sessions.getByText(/Parent report: Running late/)).toBeVisible();
    await expect(sessions.getByText("Attendance not recorded",{exact:true})).toBeVisible();
    await expect(page.getByRole("region",{name:"Saved updates",exact:true}).getByRole("article")).toHaveCount(0);
    expect(rows()).toBe("1|1|0|0");
  });
}

test("[PARENTATTEND-004] anonymous parent home offers the working sign-in route",async({page})=>{
  await page.goto("/parent");
  await expect(page.getByText("Sign in to see your child’s saved updates.",{exact:true})).toBeVisible();
  await expect(page.getByRole("region",{name:"Saved updates",exact:true})).toHaveCount(0);
  await page.getByRole("link",{name:"Sign in",exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel("Email address")).toBeVisible();
  await page.evaluate(()=>localStorage.setItem("parentplus:parent-language","hi"));
  await page.goto("/parent");
  await page.getByRole("link",{name:"साइन इन करें",exact:true}).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByLabel("Email address")).toBeVisible();
});

test("[PARENTATTEND-005] a future database item renders escaped text and only an own-child action",async({page})=>{
  test.setTimeout(180_000);
  const {sheet,parent}=await prepare(page,"UTC");
  await sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true}).click();
  await sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
  await expect(sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
  await signOut(page);await login(page,parent);await page.goto("/parent");
  const feed=page.getByRole("region",{name:"Saved updates",exact:true});
  await expect(feed.getByText("Present",{exact:true})).toBeVisible();
  const childId=await page.getByLabel("Child",{exact:true}).inputValue();
  expect(childId).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
  const sql=(query:string)=>execFileSync("docker",["--host=unix:///var/run/docker.sock","exec","-i","supabase_db_ParentPlus","psql","-XAt","-v","ON_ERROR_STOP=1","-U","postgres","-d","postgres"],{encoding:"utf8",input:query});
  // Local synthetic forward-compatibility fixture, never an application writer.
  const original=JSON.parse(sql(`select jsonb_build_object('type',type,'schema_version',schema_version,'payload',payload) from public.parent_items where child_id='${childId}';`).trim());
  const literal=(value:unknown)=>{
    const encoded=JSON.stringify(value);if(encoded.includes('$qa$'))throw new Error('Unsafe local fixture delimiter');
    return `$qa$${encoded}$qa$::jsonb`;
  };
  const payload={title:"Future class update",body:'<img src=x onerror="window.futureItemExecuted=true"> Fictional update text',action:{label:"Open saved profile",href:`/parent/children?child=${childId}`}};
  try{
    sql(`update public.parent_items set type='future_update',schema_version=99,payload=${literal({...payload,action:{label:"Unsafe action",href:"javascript:alert(1)"}})} where child_id='${childId}';`);
    await page.reload();
    await expect(feed.getByRole("heading",{name:payload.title,exact:true})).toBeVisible();
    await expect(feed.getByText(payload.body,{exact:true})).toBeVisible();
    await expect(feed.locator("img")).toHaveCount(0);await expect(feed.getByRole("link")).toHaveCount(0);
    expect(await page.evaluate(()=>Boolean((window as unknown as {futureItemExecuted?:boolean}).futureItemExecuted))).toBe(false);
    sql(`update public.parent_items set payload=${literal(payload)} where child_id='${childId}';`);
    await page.reload();
    await feed.getByRole("link",{name:"Open saved profile",exact:true}).click();
    await expect(page).toHaveURL(new RegExp(`/parent/children\\?child=${childId}$`));
    // This existing page is request-gated: a deep link does not confer child access.
    await expect(page.getByRole("button",{name:"Check creation status",exact:true})).toBeVisible();
  }finally{
    // Preserve the actual coach-written item once the synthetic fixture is checked.
    sql(`update public.parent_items set type='attendance',schema_version=${original.schema_version},payload=${literal(original.payload)} where child_id='${childId}';`);
  }
  await page.getByRole("link",{name:"Parent home",exact:true}).click();
  await expect(feed.getByText("Present",{exact:true})).toBeVisible();
});

test("[PARENTATTEND-006] one child's academy switch keeps attendance and weekly facts separate",async({page,browser})=>{
  test.setTimeout(240_000);
  const first=await prepare(page,"UTC");
  await first.sheet.getByRole("button",{name:`Present for ${CHILD}`,exact:true}).click();
  await first.sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
  await expect(first.sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
  // Separate coach browser retains independent account-bound recovery state.
  const other=await browser.newContext({baseURL:"http://127.0.0.1:3193",viewport:page.viewportSize(),isMobile:test.info().project.name==="mobile",hasTouch:test.info().project.name==="mobile"});
  let secondAcademy="";
  try{
    await other.route("**/*",route=>["http://127.0.0.1:3193","http://127.0.0.1:54321"].includes(new URL(route.request().url()).origin)?route.continue():route.abort());
    const secondPage=await other.newPage();
    const second=await prepare(secondPage,"UTC",first.parent);secondAcademy=second.academy;
    await second.sheet.getByRole("button",{name:`Absent for ${CHILD}`,exact:true}).click();
    await second.sheet.getByRole("button",{name:"Save attendance",exact:true}).click();
    await expect(second.sheet.getByText("Attendance saved.",{exact:true})).toBeVisible();
  }finally{await other.close();}
  await signOut(page);await login(page,first.parent);await page.goto("/parent");
  const academy=page.getByLabel("Academy",{exact:true});
  await expect(academy.getByRole("option")).toHaveCount(2);
  const feed=page.getByRole("region",{name:"Saved updates",exact:true});
  const week=page.getByRole("region",{name:"This week",exact:true});
  for(const [name,status,attended] of [[first.academy,"Present","1"],[secondAcademy,"Absent","0"]]){
    await academy.selectOption({label:name});
    await expect(feed.getByText(status,{exact:true})).toBeVisible();
    await expect(feed.getByRole("article")).toHaveCount(1);
    await expect(week.locator("p").filter({hasText:"Attended this week"}).locator("strong")).toHaveText(attended);
    await expect(week.locator("p").filter({hasText:"Saved attendance records"}).locator("span")).toHaveText("1");
  }
  const selected=await academy.inputValue(),batch=await page.getByLabel("Class",{exact:true}).inputValue();
  await page.getByRole("button",{name:"Refresh parent home",exact:true}).click();
  await expect(academy).toHaveValue(selected);await expect(page.getByLabel("Class",{exact:true})).toHaveValue(batch);
  await expect(feed.getByText("Absent",{exact:true})).toBeVisible();
  await expect(feed.getByText("Present",{exact:true})).toHaveCount(0);
});
