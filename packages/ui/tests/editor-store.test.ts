import { describe, it, expect, beforeEach } from "vitest";
import { useEditorStore } from "../src/state/editor-store";
import type { CaseFactSummary } from "../src/types/draft";

const baseline: CaseFactSummary = {
  parties: [
    {
      sentence_id: "s_1",
      text: "Acme v. Widgets",
      citations: [{ chunk_id: "c1", quote: "Acme" }],
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

beforeEach(() => {
  useEditorStore.setState({
    draftId: "",
    matterId: "",
    baseline: null,
    current: null,
    dirty: new Set(),
    factTimers: new Map(),
  });
});

describe("editor store", () => {
  it("reset snapshots baseline + current", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    const s = useEditorStore.getState();
    expect(s.baseline).toEqual(baseline);
    expect(s.current).toEqual(baseline);
    expect(s.current).not.toBe(s.baseline);
  });

  it("updateFactText marks dirty", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    useEditorStore
      .getState()
      .updateFactText("parties", "s_1", "Acme Corp v. Widgets Inc.");
    const s = useEditorStore.getState();
    expect(s.current!.parties[0].text).toBe("Acme Corp v. Widgets Inc.");
    expect(s.dirty.has("s_1")).toBe(true);
  });

  it("markUnsupported clears citations", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    useEditorStore.getState().markUnsupported("parties", "s_1");
    expect(useEditorStore.getState().current!.parties[0].citations).toHaveLength(0);
    expect(useEditorStore.getState().current!.parties[0].text).toBe("UNSUPPORTED");
  });

  it("addCitation does not duplicate", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    useEditorStore.getState().addCitation("parties", "s_1", { chunk_id: "c1", quote: "x" });
    useEditorStore.getState().addCitation("parties", "s_1", { chunk_id: "c1", quote: "x" });
    expect(useEditorStore.getState().current!.parties[0].citations).toHaveLength(1);
  });

  it("removeCitation drops by chunk_id", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    useEditorStore.getState().removeCitation("parties", "s_1", "c1");
    expect(useEditorStore.getState().current!.parties[0].citations).toHaveLength(0);
  });

  it("deleteFact removes from slot", () => {
    useEditorStore.getState().reset("M-1", "D-1", baseline);
    useEditorStore.getState().deleteFact("parties", "s_1");
    expect(useEditorStore.getState().current!.parties).toHaveLength(0);
  });
});
