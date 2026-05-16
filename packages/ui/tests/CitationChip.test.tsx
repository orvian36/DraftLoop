import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { CitationChip } from "../src/components/CitationChip";

describe("CitationChip", () => {
  it("fires onResolve when clicked", () => {
    const on = vi.fn();
    render(
      <CitationChip citation={{ chunk_id: "c1", quote: "x" }} onResolve={on} />,
    );
    fireEvent.click(screen.getByRole("button", { name: /c1/i }));
    expect(on).toHaveBeenCalledWith("c1");
  });

  it("renders × when onRemove supplied", () => {
    const on = vi.fn();
    const off = vi.fn();
    render(
      <CitationChip
        citation={{ chunk_id: "c1", quote: "x" }}
        onResolve={on}
        onRemove={off}
      />,
    );
    fireEvent.click(screen.getByLabelText("remove citation c1"));
    expect(off).toHaveBeenCalledWith("c1");
    expect(on).not.toHaveBeenCalled();
  });
});
