import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CaseFactSummaryEditor } from "../src/components/CaseFactSummaryEditor";
import type { CaseFactSummary } from "../src/types/draft";

const initial: CaseFactSummary = {
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

describe("CaseFactSummaryEditor", () => {
  it("renders the fact text in a textarea", () => {
    render(
      <CaseFactSummaryEditor
        matterId="M-1"
        draftId="D-1"
        initial={initial}
        onResolveCitation={vi.fn()}
        onSave={vi.fn()}
      />,
    );
    const textarea = screen.getByLabelText("fact s_1 text") as HTMLTextAreaElement;
    expect(textarea.value).toBe("Acme v. Widgets");
  });

  it("calls onSave with current state on Save click", () => {
    const onSave = vi.fn();
    render(
      <CaseFactSummaryEditor
        matterId="M-1"
        draftId="D-1"
        initial={initial}
        onResolveCitation={vi.fn()}
        onSave={onSave}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalled();
    const calledWith = onSave.mock.calls[0][0];
    expect(calledWith.parties[0].sentence_id).toBe("s_1");
  });

  it("mark UNSUPPORTED clears citations", () => {
    render(
      <CaseFactSummaryEditor
        matterId="M-1"
        draftId="D-1"
        initial={initial}
        onResolveCitation={vi.fn()}
        onSave={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("mark UNSUPPORTED"));
    const textarea = screen.getByLabelText("fact s_1 text") as HTMLTextAreaElement;
    expect(textarea.value).toBe("UNSUPPORTED");
  });
});
