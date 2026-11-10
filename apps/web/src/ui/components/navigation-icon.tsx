/** Outline icons matching the founder's Coach/Tutor HTML reference. */
export function NavigationIcon({
  name,
}: {
  name: "home" | "calendar" | "plus" | "students" | "wallet";
}) {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {name === "home" && (
        <path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />
      )}
      {name === "calendar" && (
        <>
          <rect x="3.5" y="5" width="17" height="15" rx="3" />
          <path d="M3.5 10h17M8 3v4M16 3v4" />
        </>
      )}
      {name === "plus" && <path d="M12 5v14M5 12h14" />}
      {name === "students" && (
        <>
          <circle cx="9" cy="8" r="3.2" />
          <path d="M3 19c.6-3.3 3-5 6-5s5.4 1.7 6 5M15.5 4.8a3 3 0 0 1 0 5.9M17.5 14.3c1.8.6 3 2.2 3.4 4.7" />
        </>
      )}
      {name === "wallet" && (
        <>
          <rect x="3" y="6" width="18" height="14" rx="3" />
          <path d="M3 10h18M16 15h2" />
        </>
      )}
    </svg>
  );
}
