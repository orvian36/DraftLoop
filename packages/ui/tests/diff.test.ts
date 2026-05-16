import { describe, it, expect } from "vitest";
import { diffSummaries } from "../src/state/diff";
import type { CaseFactSummary } from "../src/types/draft";

const base: CaseFactSummary = {
  parties: [
    {
      sentence_id: "s_1",
      text: "Acme",
      citations: [{ chunk_id: "c1", quote: "x" }],
      confidence: "high",
    },
  ],
  jurisdiction: [],
  key_dates: [],
  claims: [],
  relief_sought: [],
  procedural_posture: [],
  key_evidence: [],
};

const ctx = {
  draftId: "D-1",
  matterId: "M-1",
  operatorId: "op",
  draftModelVersion: "v1",
  promptHash: "h",
  factStartTimers: new Map<string, number>(),
};

describe("diffSummaries", () => {
  it("emits fact_text_changed when text differs", () => {
    const next = structuredClone(base);
    next.parties[0].text = "Acme Corp";
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "fact_text_changed")).toBe(true);
  });

  it("emits fact_marked_unsupported with sentinel", () => {
    const next = structuredClone(base);
    next.parties[0].text = "UNSUPPORTED";
    next.parties[0].citations = [];
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "fact_marked_unsupported")).toBe(true);
  });

  it("emits citation_added and citation_removed", () => {
    const next = structuredClone(base);
    next.parties[0].citations = [{ chunk_id: "c2", quote: "y" }];
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "citation_added")).toBe(true);
    expect(events.some((e) => e.op === "citation_removed")).toBe(true);
  });

  it("emits fact_deleted when fact removed", () => {
    const next = structuredClone(base);
    next.parties = [];
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "fact_deleted")).toBe(true);
  });

  it("emits fact_added when fact appears", () => {
    const next = structuredClone(base);
    next.parties.push({
      sentence_id: "s_2",
      text: "new",
      citations: [{ chunk_id: "c2", quote: "y" }],
      confidence: "high",
    });
    const events = diffSummaries(base, next, ctx);
    expect(events.some((e) => e.op === "fact_added")).toBe(true);
  });
});
