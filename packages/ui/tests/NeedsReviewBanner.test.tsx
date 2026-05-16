import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { NeedsReviewBanner } from "../src/components/NeedsReviewBanner";

describe("NeedsReviewBanner", () => {
  it("renders nothing when count is zero", () => {
    const { container } = render(<NeedsReviewBanner count={0} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders alert when count > 0", () => {
    render(<NeedsReviewBanner count={3} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/3 low-confidence spans/);
  });

  it("singular form when count is 1", () => {
    render(<NeedsReviewBanner count={1} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/1 low-confidence span /);
  });
});
