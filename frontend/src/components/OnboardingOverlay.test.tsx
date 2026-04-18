import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OnboardingOverlay } from "./OnboardingOverlay";

describe("OnboardingOverlay", () => {
  it("keeps finish action available on the final step", async () => {
    const user = userEvent.setup();
    const onNext = vi.fn();

    render(
      <OnboardingOverlay
        open
        roleLabel="Player"
        steps={[
          { anchorId: "first", title: "First", detail: "First step" },
          { anchorId: "final", title: "Final", detail: "Final step" },
        ]}
        stepIndex={1}
        onNext={onNext}
        onBack={vi.fn()}
        onSkip={vi.fn()}
        onReplay={vi.fn()}
        canReplay={false}
        canAdvance={false}
      />,
    );

    const finishButton = screen.getByRole("button", { name: "Finish" });
    expect((finishButton as HTMLButtonElement).disabled).toBe(false);
    await user.click(finishButton);
    expect(onNext).toHaveBeenCalledTimes(1);
  });
});
