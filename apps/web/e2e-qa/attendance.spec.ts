import { test, expect, login, emailFor, workspace, child, setup } from "./fixtures";
import type { Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
const BATCH="QA Attendance Juniors", CHILD="Fictional Attendance Child";
async function signOut(page: Page) {
  await page.goto("/login");
  await page.getByRole("button",{name:"Sign out",exact:true}).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
}
async function prepare(page: Page) {
  const coach=emailFor(); await login(page,coach);
  const academy=await workspace(page,"academy");
  const today=new Intl.DateTimeFormat("en-CA",{timeZone:"Asia/Kolkata",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date());
  const p=await setup(page);
  await p.getByLabel("Course name",{exact:true}).fill("QA Attendance Clay");
  await p.getByLabel("Batch name",{exact:true}).fill(BATCH);
  await p.getByLabel("Academy time zone",{exact:true}).fill("Asia/Kolkata");
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
  await signOut(page); const parent=await login(page); await child(page,CHILD);
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
