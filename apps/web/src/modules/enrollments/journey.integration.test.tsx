import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
const m = vi.hoisted(() => ({
  create: vi.fn(),
  getUser: vi.fn(),
  rpc: vi.fn(),
}));
vi.mock("@/lib/supabase/server", () => ({ createClient: m.create }));
vi.mock("@/lib/auth/session-observer", () => ({
  observeSessionChanges: () => () => {},
}));
import EnrollmentPanel from "./enrollment-panel";
import ParentClassesPanel from "./parent-classes-panel";
const owner = "11111111-1111-4111-8111-111111111111",
  parent = "22222222-2222-4222-8222-222222222222",
  workspace = "33333333-3333-4333-8333-333333333333",
  batch = "44444444-4444-4444-8444-444444444444",
  child = "55555555-5555-4555-8555-555555555555",
  enrollment = "66666666-6666-4666-8666-666666666666";
beforeEach(() => {
  vi.resetAllMocks();
  vi.stubEnv("NEXT_PUBLIC_ENABLE_LIVE_OTP", "true");
  localStorage.clear();
});
it("uses real panels and actions to recover an original receipt then show the current class to its parent", async () => {
  let actor = owner,
    status: string | null = null,
    version = 0,
    lost = true;
  const receipts = new Map<
    string,
    { enrollment_id: string; status: string; version: number }
  >();
  m.getUser.mockImplementation(async () => ({
    data: { user: { id: actor } },
    error: null,
  }));
  const query = {
    select: () => query,
    eq: () => query,
    in: () => query,
    limit: async () => ({
      data: [
        {
          workspace_id: workspace,
          workspaces: {
            id: workspace,
            name: "Sunrise Academy",
            status: "active",
          },
        },
      ],
      error: null,
    }),
  };
  m.create.mockResolvedValue({
    auth: { getUser: m.getUser },
    from: () => query,
    rpc: m.rpc,
  });
  m.rpc.mockImplementation(
    async (name: string, args: Record<string, unknown> = {}) => {
      if (name === "app_enrollment_batches")
        return {
          data: [
            { batch_id: batch, batch_name: "Morning", course_name: "Maths" },
          ],
          error: null,
        };
      if (name === "app_enrollment_candidates")
        return { data: [{ child_id: child, child_name: "Asha" }], error: null };
      if (name === "app_batch_enrollments")
        return {
          data: status
            ? [
                {
                  enrollment_id: enrollment,
                  child_id: child,
                  child_name: "Asha",
                  status,
                  version,
                },
              ]
            : [],
          error: null,
        };
      if (name === "app_save_enrollment") {
        const request = String(args.p_request_id);
        if (!receipts.has(request)) {
          status = "active";
          version = 1;
          receipts.set(request, { enrollment_id: enrollment, status, version });
        }
        if (lost) {
          lost = false;
          throw Error("synthetic committed write with lost reply");
        }
        return { data: [receipts.get(request)], error: null };
      }
      if (name === "app_list_created_children")
        return {
          data: [{ child_id: child, display_name: "Asha" }],
          error: null,
        };
      if (name === "app_parent_enrollments")
        return {
          data: status
            ? [
                {
                  enrollment_id: enrollment,
                  academy_name: "Sunrise Academy",
                  batch_name: "Morning",
                  course_name: "Maths",
                  status,
                  version,
                },
              ]
            : [],
          error: null,
        };
      throw Error(`Unexpected synthetic RPC: ${name}`);
    },
  );
  const manager = render(<EnrollmentPanel />);
  await screen.findByRole("button", { name: "Morning" });
  fireEvent.change(screen.getByLabelText("Connected child"), {
    target: { value: child },
  });
  fireEvent.click(screen.getByRole("button", { name: "Enrol child" }));
  await screen.findByRole("alert");
  // A concurrent manager changes the current record after the original save.
  status = "paused";
  version = 2;
  fireEvent.click(
    screen.getByRole("button", { name: "Check enrolment status" }),
  );
  expect(await screen.findByText("Paused")).toBeVisible();
  expect(
    screen.queryByText("Active", { selector: "span" }),
  ).not.toBeInTheDocument();
  const writes = m.rpc.mock.calls.filter(
    ([name]) => name === "app_save_enrollment",
  );
  expect(writes).toHaveLength(2);
  expect(writes[1]).toEqual(writes[0]);
  expect(receipts.size).toBe(1);
  manager.unmount();
  actor = parent;
  render(<ParentClassesPanel />);
  expect(await screen.findByText("Sunrise Academy")).toBeVisible();
  expect(screen.getByText("Paused")).toBeVisible();
  await waitFor(() =>
    expect(m.rpc).toHaveBeenLastCalledWith("app_parent_enrollments", {
      p_child_id: child,
    }),
  );
});
function rejectedProvider(initialStatus: string, stale: boolean) {
  let status = initialStatus,
    version = 1,
    reject = true;
  m.getUser.mockResolvedValue({ data: { user: { id: owner } }, error: null });
  const query = {
    select: () => query,
    eq: () => query,
    in: () => query,
    limit: async () => ({
      data: [
        {
          workspace_id: workspace,
          workspaces: {
            id: workspace,
            name: "Sunrise Academy",
            status: "active",
          },
        },
      ],
      error: null,
    }),
  };
  m.create.mockResolvedValue({
    auth: { getUser: m.getUser },
    from: () => query,
    rpc: m.rpc,
  });
  m.rpc.mockImplementation(
    async (name: string, args: Record<string, unknown> = {}) => {
      if (name === "app_enrollment_batches")
        return {
          data: [
            { batch_id: batch, batch_name: "Morning", course_name: "Maths" },
          ],
          error: null,
        };
      if (name === "app_enrollment_candidates")
        return { data: [{ child_id: child, child_name: "Asha" }], error: null };
      if (name === "app_batch_enrollments")
        return {
          data: [
            {
              enrollment_id: enrollment,
              child_id: child,
              child_name: "Asha",
              status,
              version,
            },
          ],
          error: null,
        };
      if (name === "app_save_enrollment")
        return {
          data: null,
          error: { code: "23505", message: "private saved-state conflict" },
        };
      if (name === "app_change_enrollment") {
        if (stale && reject) {
          status = "paused";
          version = 2;
          reject = false;
          return {
            data: null,
            error: { code: "40001", message: "private stale version" },
          };
        }
        status = String(args.p_status);
        version++;
        return {
          data: [{ enrollment_id: enrollment, status, version }],
          error: null,
        };
      }
      throw Error(`Unexpected synthetic RPC: ${name}`);
    },
  );
}
it("reconciles a rejected stale edit and waits for an explicit action using the refreshed version and new UUID", async () => {
  rejectedProvider("active", true);
  render(<EnrollmentPanel />);
  await screen.findByText("Active");
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "This change was not saved",
  );
  expect(await screen.findByText("Paused")).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Refresh enrolments" }),
  ).toBeEnabled();
  expect(screen.getByLabelText("Connected child")).toBeEnabled();
  expect(screen.getByLabelText("Academy for enrolment")).toBeEnabled();
  expect(
    screen.queryByRole("button", { name: "Check enrolment status" }),
  ).not.toBeInTheDocument();
  expect(
    m.rpc.mock.calls.filter(([name]) => name === "app_change_enrollment"),
  ).toHaveLength(1);
  fireEvent.click(screen.getByRole("button", { name: "Complete enrolment" }));
  expect(await screen.findByText("Completed")).toBeVisible();
  const writes = m.rpc.mock.calls.filter(
    ([name]) => name === "app_change_enrollment",
  );
  expect(writes).toHaveLength(2);
  expect(writes[0][1]).toMatchObject({
    p_expected_version: 1,
    p_status: "completed",
  });
  expect(writes[1][1]).toMatchObject({
    p_expected_version: 2,
    p_status: "completed",
  });
  expect(writes[1][1].p_request_id).not.toBe(writes[0][1].p_request_id);
});
async function assertSavedConflict(status: string, label: string) {
  rejectedProvider(status, false);
  render(<EnrollmentPanel />);
  await screen.findByText(label);
  fireEvent.change(screen.getByLabelText("Connected child"), {
    target: { value: child },
  });
  fireEvent.click(screen.getByRole("button", { name: "Enrol child" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "This change was not saved",
  );
  expect(screen.getByText(label)).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Refresh enrolments" }),
  ).toBeEnabled();
  expect(screen.getByLabelText("Connected child")).toBeEnabled();
  expect(
    screen.queryByRole("button", { name: "Check enrolment status" }),
  ).not.toBeInTheDocument();
  expect(
    m.rpc.mock.calls.filter(([name]) => name === "app_save_enrollment"),
  ).toHaveLength(1);
  expect(
    m.rpc.mock.calls.filter(([name]) => name === "app_batch_enrollments"),
  ).toHaveLength(2);
  expect(
    m.rpc.mock.calls.filter(([name]) => name === "app_change_enrollment"),
  ).toHaveLength(0);
}
it("reconciles a paused natural-key save conflict without silently resuming the enrolment", async () => {
  await assertSavedConflict("paused", "Paused");
});
it("reconciles a terminal natural-key save conflict without reopening the enrolment", async () => {
  await assertSavedConflict("withdrawn", "Withdrawn");
  expect(
    screen.queryByRole("button", { name: "Resume enrolment" }),
  ).not.toBeInTheDocument();
});
