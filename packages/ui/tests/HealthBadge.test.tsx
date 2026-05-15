import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { HealthBadge } from "../src/components/HealthBadge";

describe("HealthBadge", () => {
  it("renders the label", () => {
    render(<HealthBadge ok={true} label="API healthy" />);
    expect(screen.getByRole("status")).toHaveTextContent("API healthy");
  });

  it("applies emerald classes when ok=true", () => {
    render(<HealthBadge ok={true} label="OK" />);
    expect(screen.getByRole("status").className).toContain("emerald");
  });

  it("applies rose classes when ok=false", () => {
    render(<HealthBadge ok={false} label="Down" />);
    expect(screen.getByRole("status").className).toContain("rose");
  });
});
