export function DashboardStats() {
  return (
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
  );
}
