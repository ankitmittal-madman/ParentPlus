import { test, expect, login, emailFor, workspace, child, setup, schedule, membership } from "./fixtures";

test("[AUTH-001] validates empty and malformed email", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Enter a valid email" })).toBeVisible();
  await page.getByLabel("Email address").fill("invalid");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Enter a valid email" })).toBeVisible();
});
test("[AUTH-002] rejects non-fictional email", async ({ page }) => {
  await page.goto("/login");await page.getByLabel("Email address").fill("parent@example.com");
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Founder sign-in is unavailable" })).toBeVisible();
});
test("[AUTH-003] wrong code and another request", async ({ page }) => {
  await page.goto("/login");await page.getByLabel("Email address").fill(emailFor());
  await page.getByRole("button", { name: "Continue", exact: true }).click();
  await page.getByLabel("Verification code").fill("12");
  await page.getByRole("button", { name: "Verify code", exact: true }).click();
  await expect(page.locator('p[role="alert"]')).toBeVisible();
  await page.getByLabel("Verification code").fill("000000");
  await page.getByRole("button", { name: "Verify code", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Founder sign-in is unavailable" })).toBeVisible();
  await page.getByRole("button", { name: "Request another code", exact: true }).click();
  await expect(page.getByLabel("Verification code")).toBeVisible();
});
test("[AUTH-004] signup toggle and dummy session", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByText("Create an account with your email.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Sign in instead", exact: true }).click();
  await login(page);
  await expect(page.getByRole("link", { name: "View profiles you created" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Continue to coach area" })).toBeVisible();
});
test("[AUTH-005] sign-out removes access", async ({ page }) => {
  await login(page);await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await expect(page.getByRole("link", { name: "Continue to coach area" })).toHaveCount(0);
  await page.goto("/schedule");await expect(page).toHaveURL(/\/login$/);
});
test("[AUTH-006] anonymous protected routes", async ({ page }) => {
  for (const route of ["/", "/schedule", "/students", "/post", "/fees"]) {
    await test.step(`Anonymous ${route} redirects to login`, async () => {
      await page.goto(route);await expect(page).toHaveURL(/\/login$/);
    });
  }
});
test("[PARENT-001] new account empty list", async ({ page }) => {
  await login(page);await page.getByRole("link", { name: "View profiles you created" }).click();
  await page.getByRole("button", { name: "Load profiles", exact: true }).click();
  await expect(page.getByText(/No profiles/)).toBeVisible();
});
test("[PARENT-002] child name validation", async ({ page }) => {
  await login(page);await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  await page.getByRole("button", { name: "Create profile", exact: true }).click();
  await expect(page.getByRole("region", { name: "Create a child profile" }).getByRole("alert")).toContainText("120 characters");
  await page.getByLabel("Child name").fill("x".repeat(121));
  await page.getByRole("button", { name: "Create profile", exact: true }).click();
  await expect(page.getByRole("region", { name: "Create a child profile" }).getByRole("alert")).toContainText("120 characters");
});
test("[PARENT-003] persist child through reload", async ({ page }) => {
  await login(page);await child(page);
  await page.getByRole("button", { name: "Load profiles", exact: true }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "Fictional QA Child" })).toHaveCount(1);
  await page.reload();await page.getByRole("button", { name: "Load profiles", exact: true }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "Fictional QA Child" })).toHaveCount(1);
});
test("[PARENT-004] add a second child", async ({ page }) => {
  await login(page);await child(page,"Fictional First");
  await page.getByRole("button", { name: "Add another profile", exact: true }).click();
  await page.getByLabel("Child name").fill("Fictional Second");
  await page.getByRole("button", { name: "Create profile", exact: true }).click();
  await page.getByRole("button", { name: "Confirm result", exact: true }).click();
  await page.getByRole("button", { name: "Load profiles", exact: true }).click();
  await expect(page.getByRole("listitem").filter({ hasText: "Fictional First" })).toHaveCount(1);
  await expect(page.getByRole("listitem").filter({ hasText: "Fictional Second" })).toHaveCount(1);
});
test("[PARENT-005] account isolation", async ({ page }) => {
  await login(page);await child(page,"Fictional Private QA Child");
  await page.goto("/login");await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await login(page);await page.goto("/parent/children");
  await page.getByRole("button", { name: "Load profiles", exact: true }).click();
  await expect(page.getByText(/No profiles/)).toBeVisible();
  await expect(page.getByText("Fictional Private QA Child", { exact: true })).toHaveCount(0);
});
test("[PARENT-006] recover unacknowledged child", async ({ page }) => {
  await login(page);await child(page,"Fictional Recovered Child",false);
  await page.reload();await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  await expect(page.getByText("Profile: Fictional Recovered Child", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Confirm result", exact: true }).click();
  await expect(page.getByText("Result confirmed", { exact: true })).toBeVisible();
});
test("[PARENT-007] fence interrupted creation", async ({ page }) => {
  await login(page);await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  let injected = false;
  await page.route("**/parent/children", route => {
    const request = route.request();
    if (!injected && request.method() === "POST" && (request.postData() || "").includes('"operation":"begin"')) { injected = true; return route.abort(); }
    return route.fallback();
  });
  await page.getByLabel("Child name").fill("Fictional Interrupted");
  await page.getByRole("button", { name: "Create profile", exact: true }).click();
  await expect(page.getByRole("region", { name: "Create a child profile" }).getByRole("alert")).toContainText("Unable to confirm");
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  expect(injected).toBe(true);
  await page.getByRole("button", { name: "Stop waiting for this request", exact: true }).click();
  await expect(page.getByRole("region", { name: "Create a child profile" }).getByRole("alert")).toContainText("cannot create a profile");
  await page.getByLabel("Child name").fill("Fictional Fresh Request");
  await page.getByRole("button", { name: "Create profile", exact: true }).click();
  await expect(page.getByText("Profile: Fictional Fresh Request", { exact: true })).toBeVisible();
});
test("[WORKSPACE-001] access guidance and sign-out", async ({ page }) => {
  await login(page);await page.getByRole("link", { name: "Continue to coach area" }).click();
  await expect(page).toHaveURL(/\/coach-access$/);
  await page.getByRole("link", { name: "Set up your own workspace" }).click();
  await expect(page).toHaveURL(/\/coach-onboarding$/);
  await page.goto("/coach-access");await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
});
test("[WORKSPACE-002] independent workspace recovery", async ({ page }) => {
  await login(page);await workspace(page);
  await page.reload();await page.getByRole("button", { name: "Check workspace setup", exact: true }).click();
  await expect(page.getByText("Workspace setup confirmed.", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Continue to class setup" }).click();
  await expect(page.getByRole("heading", { name: "Schedule", exact: true })).toBeVisible();
});
test("[WORKSPACE-003] academy workspace", async ({ page }) => {
  await login(page);await workspace(page,"academy");
  await page.getByRole("link", { name: "Continue to class setup" }).click();
  await expect(page.getByRole("heading", { name: "Schedule", exact: true })).toBeVisible();
});
test("[WORKSPACE-004] native workspace validation", async ({ page }) => {
  await login(page);await page.goto("/coach-onboarding");
  await page.getByRole("button", { name: "Check workspace setup", exact: true }).click();
  await page.getByRole("button", { name: "Create workspace", exact: true }).click();
  expect(await page.getByLabel("Workspace name").evaluate((e: HTMLInputElement) => e.validity.valid)).toBe(false);
  await page.getByLabel("Workspace name").fill("x");
  await page.getByRole("button", { name: "Create workspace", exact: true }).click();
  expect(await page.getByLabel("Workspace name").evaluate((e: HTMLInputElement) => e.validity.valid)).toBe(false);
  await expect(page.getByRole("link", { name: "Continue to class setup" })).toHaveCount(0);
});
test("[WORKSPACE-005] corrupt setup marker", async ({ page }) => {
  await login(page);await page.goto("/coach-onboarding");
  await page.evaluate(() => localStorage.setItem("parentplus.workspace-first-use.v1", "invalid-qa-marker"));
  await page.getByRole("button", { name: "Check workspace setup", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Saved request information is unavailable");
  await expect(page.getByRole("button", { name: "Create workspace", exact: true })).toHaveCount(0);
});
test("[CLASS-001] practice validation and preview", async ({ page }) => {
  await login(page);await workspace(page);await page.goto("/schedule");
  const panel=page.getByRole("region", { name: "Try class setup", exact: true });
  await panel.getByRole("button", { name: "Preview class setup" }).click();
  await expect(panel.getByRole("alert")).toContainText("Enter both");
  await panel.getByLabel("Course name").fill("Example Practice");await panel.getByLabel("Batch name").fill("Example Juniors");
  await panel.getByRole("button", { name: "Preview class setup" }).click();
  await expect(panel.getByRole("status")).toContainText("Preview only — not saved");
});
test("[CLASS-002] weekly class persistence and acknowledgement", async ({ page }) => {
  await login(page);await workspace(page,"academy");await schedule(page);
  await page.reload();const panel=await setup(page);
  await expect(panel.getByText("Course: QA Clay Basics", { exact: true })).toBeVisible();
  await expect(panel.getByText("Weekly schedule: 3 sessions", { exact: true })).toBeVisible();
  await panel.getByRole("button", { name: "Confirm course, batch and schedule", exact: true }).click();
  await expect(panel.getByText("Setup completed — acknowledged", { exact: true })).toBeVisible();
});
test("[CLASS-003] invalid weekly schedule", async ({ page }) => {
  await login(page);await workspace(page,"academy");const panel=await setup(page);
  await panel.getByLabel("Course name", { exact: true }).fill("QA Invalid");await panel.getByLabel("Batch name", { exact: true }).fill("QA Batch");
  await panel.getByLabel("Academy time zone").fill("Unknown/Zone");
  await panel.getByLabel("First session date").fill("2026-11-16");await panel.getByLabel("Local start time").fill("17:00");
  await panel.getByLabel("Last date for weekly sessions").fill("2026-11-30");
  await panel.getByRole("button", { name: "Create course, batch and weekly sessions", exact: true }).click();
  await expect(panel.getByRole("status").filter({ hasText: "Enter a valid workspace time zone." })).toBeVisible();
  await expect(panel.getByLabel("Course name", { exact: true })).toBeVisible();
  await panel.getByLabel("Academy time zone").fill("Asia/Kolkata");await panel.getByLabel("Last date for weekly sessions").fill("2026-11-01");
  await panel.getByRole("button", { name: "Create course, batch and weekly sessions", exact: true }).click();
  await expect(panel.getByRole("status").filter({ hasText: "The end date must not precede the start date." })).toBeVisible();
  await expect(panel.getByLabel("Course name", { exact: true })).toBeVisible();
  await expect(panel.getByLabel("Saved weekly schedule")).toHaveCount(0);
});
test("[CLASS-004] second course after acknowledgement", async ({ page }) => {
  await login(page);await workspace(page);const first=await schedule(page,"QA First Course");
  await first.getByRole("button", { name: "Confirm course, batch and schedule", exact: true }).click();
  await expect(first.getByText("Setup completed — acknowledged", { exact: true })).toBeVisible();
  const second=await schedule(page,"QA Second Course");
  await expect(second.getByText("Course: QA Second Course", { exact: true })).toBeVisible();
});
test("[ACCESS-001] suspend and restore owner", async ({ page }) => {
  const email=await login(page);const name=await workspace(page,"academy");
  await membership(page,email,name,"suspended");await page.goto("/schedule");await expect(page).toHaveURL(/\/coach-access$/);
  await membership(page,email,name,"active");await page.goto("/schedule");
  await expect(page.getByRole("heading", { name: "Schedule", exact: true })).toBeVisible();
});
test("[ACCESS-002] role and removed access", async ({ page }) => {
  const email=await login(page);const name=await workspace(page);
  await membership(page,email,name,"active","admin");const panel=await setup(page);
  await expect(panel.getByLabel("Course name", { exact: true })).toBeVisible();
  await membership(page,email,name,"active","coach");await page.goto("/schedule");
  await page.getByRole("button", { name: "Load academies", exact: true }).click();
  await expect(page.getByText("No eligible academies were found.", { exact: true })).toBeVisible();
  await membership(page,email,name,"removed","coach");await page.goto("/schedule");await expect(page).toHaveURL(/\/coach-access$/);
});
test("[FOUNDER-001] counts and console links", async ({ page }) => {
  await page.goto("/login");await page.getByRole("link", { name: "Open founder controls" }).click();
  await page.getByRole("button", { name: "Refresh test records" }).click();
  await expect(page.getByText("children", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Parent profiles", exact: true }).click();await expect(page).toHaveURL(/\/parent\/children$/);
  await page.goto("/founder");await page.getByRole("link", { name: "Switch test account" }).click();await expect(page).toHaveURL(/\/login$/);
  await page.goto("/founder");await page.getByRole("link", { name: "Create workspace", exact: true }).click();await expect(page).toHaveURL(/\/coach-onboarding$/);
  await page.goto("/founder");await page.getByRole("link", { name: "Coach classes", exact: true }).click();await expect(page).toHaveURL(/\/login$/);
});
test("[FOUNDER-002] incomplete membership disabled", async ({ page }) => {
  await page.goto("/founder");await page.getByRole("button", { name: "Refresh test records" }).click();
  await expect(page.getByRole("button", { name: "Apply test access", exact: true })).toBeDisabled();
});
test("[NAV-001] bottom navigation and menu", async ({ page }) => {
  await login(page);await workspace(page);await page.goto("/");
  const openMenu = async () => {
    const menu = page.getByRole("navigation", { name: "Coach menu" });
    await expect(page.getByRole("heading", { name: "Good morning, Meera", exact: true })).toBeVisible();
    const details = page.getByRole("main").locator("details");
    if (!await details.evaluate(element => element.hasAttribute("open"))) await details.locator("summary").click();
    await expect(details).toHaveAttribute("open", "");
    await expect(menu).toBeVisible();
  };
  await expect(page.getByText("Example data only — these are not real classes or records.", { exact: true })).toBeVisible();
  await page.locator("summary").click();await expect(page.getByRole("navigation", { name: "Coach menu" })).toBeVisible();
  await page.locator("summary").click();
  const destinations = [["Schedule","/schedule"],["Students","/students"],["Post","/post"],["Fees","/fees"],["Today","/"]];
  for (const origin of ["/", "/schedule", "/students", "/post", "/fees"]) {
    for (const [name, route] of destinations) {
      await page.goto(origin);
      await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name, exact: true }).click();
      await expect(page).toHaveURL(new RegExp(route === "/" ? "/$" : route + "$"));
      if (["/students", "/post", "/fees"].includes(route)) await expect(page.getByRole("main").getByText("Coming soon", { exact: true })).toBeVisible();
    }
  }
  await page.goto("/");
  await openMenu();await page.getByRole("navigation", { name: "Coach menu" }).getByRole("link", { name: "Schedule", exact: true }).click();await expect(page).toHaveURL(/\/schedule$/);
  await page.getByRole("navigation", { name: "Main navigation" }).getByRole("link", { name: "Today", exact: true }).click();
  await openMenu();await page.getByRole("navigation", { name: "Coach menu" }).getByRole("link", { name: "Today", exact: true }).click();await expect(page).toHaveURL(/\/$/);
  await openMenu();await page.getByRole("navigation", { name: "Coach menu" }).getByRole("link", { name: "Sign in", exact: true }).click();await expect(page).toHaveURL(/\/login$/);
});
test("[LAYOUT-001] key screens fit viewport", async ({ page }) => {
  await login(page);await workspace(page);
  for (const route of ["/login","/parent/children","/coach-onboarding","/founder","/schedule"]) {
    await page.goto(route);await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
});

test("[AUTH-007] retry session check after local network failure", async ({ page }) => {
  await login(page);
  await page.route("**/auth/v1/user", route => route.abort());
  await page.reload();
  await expect(page.getByRole("button", { name: "Try again", exact: true })).toBeVisible();
  await page.unroute("**/auth/v1/user");
  await page.getByRole("button", { name: "Try again", exact: true }).click();
  await expect(page.getByText("Signed in.", { exact: true })).toBeVisible();
});
test("[AUTH-008] recover uncertain sign-out", async ({ page }) => {
  await login(page);
  await page.route("**/auth/v1/logout?**", route => route.fulfill({ status: 503, contentType: "application/json", body: '{"message":"Synthetic local fault"}' }));
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page.getByRole("button", { name: "Check session", exact: true })).toBeVisible();
  await page.unroute("**/auth/v1/logout?**");
  await page.getByRole("button", { name: "Check session", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await expect(page.getByRole("link", { name: "Continue to coach area" })).toHaveCount(0);
});
test("[PARENT-008] retry the same interrupted creation", async ({ page }) => {
  await login(page);await page.goto("/parent/children");
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  let injected=false;
  await page.route("**/parent/children", route => {
    if (!injected && route.request().method()==="POST" && (route.request().postData()||"").includes('"operation":"begin"')) { injected=true;return route.abort(); }
    return route.fallback();
  });
  await page.getByLabel("Child name").fill("Fictional Retried Child");
  await page.getByRole("button", { name: "Create profile", exact: true }).click();
  await expect(page.getByRole("region", { name: "Create a child profile" }).getByRole("alert")).toContainText("Unable to confirm");
  expect(injected).toBe(true);
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  await page.getByRole("button", { name: "Retry same request", exact: true }).click();
  await expect(page.getByText("Profile: Fictional Retried Child", { exact: true })).toBeVisible();
});
test("[PARENT-009] retry an interrupted confirmation", async ({ page }) => {
  await login(page);await child(page,"Fictional Retry Confirmation",false);
  let injected=false;
  await page.route("**/parent/children", route => {
    if (!injected && route.request().method()==="POST" && (route.request().postData()||"").includes('"operation":"ack"')) { injected=true;return route.abort(); }
    return route.fallback();
  });
  await page.getByRole("button", { name: "Confirm result", exact: true }).click();
  await expect(page.getByRole("region", { name: "Create a child profile" }).getByRole("alert")).toContainText("Unable to confirm");
  expect(injected).toBe(true);
  await page.getByRole("button", { name: "Check creation status", exact: true }).click();
  await page.getByRole("button", { name: "Retry confirmation", exact: true }).click();
  await expect(page.getByText("Result confirmed", { exact: true })).toBeVisible();
});
test("[CLASS-005] finish a saved pending setup after interruption", async ({ page }) => {
  await login(page);await workspace(page);let panel=await setup(page);
  let injected=false;
  await page.route("**/schedule", route => {
    if (!injected && route.request().method()==="POST" && (route.request().postData()||"").includes('"operation":"complete"')) { injected=true;return route.abort(); }
    return route.fallback();
  });
  await panel.getByLabel("Course name", { exact: true }).fill("QA Pending Course");
  await panel.getByLabel("Batch name", { exact: true }).fill("QA Pending Batch");
  await panel.getByLabel("Academy time zone").fill("Asia/Kolkata");
  await panel.getByLabel("First session date").fill("2026-11-16");
  await panel.getByLabel("Local start time").fill("17:00");
  await panel.getByLabel("Last date for weekly sessions").fill("2026-11-30");
  await panel.getByRole("button", { name: "Create course, batch and weekly sessions", exact: true }).click();
  await expect(panel.getByText("Setup pending", { exact: true })).toBeVisible();expect(injected).toBe(true);
  await page.reload();panel=await setup(page);
  await panel.getByLabel("Academy time zone").fill("Asia/Kolkata");
  await panel.getByLabel("First session date").fill("2026-11-16");
  await panel.getByLabel("Local start time").fill("17:00");
  await panel.getByLabel("Last date for weekly sessions").fill("2026-11-30");
  await panel.getByRole("button", { name: "Finish course, batch and schedule", exact: true }).click();
  await expect(panel.getByText("Weekly schedule: 3 sessions", { exact: true })).toBeVisible();
});
