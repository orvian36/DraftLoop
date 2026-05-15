import { HealthBadge } from "@draftloop/ui";

export default async function Home() {
  let apiHealthy = false;
  try {
    const res = await fetch("http://localhost:8000/health", { cache: "no-store" });
    apiHealthy = res.ok;
  } catch {
    apiHealthy = false;
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">DraftLoop</h1>
      <p className="mt-3 text-slate-600">
        Grounded legal drafting with an improvement-from-edits loop.
      </p>
      <div className="mt-8">
        <HealthBadge ok={apiHealthy} label={apiHealthy ? "API healthy" : "API unreachable"} />
      </div>
    </main>
  );
}
