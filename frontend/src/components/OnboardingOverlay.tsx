import { useEffect, useMemo, useState } from "react";
import type { OnboardingStep } from "../lib/onboardingModel";

type OnboardingOverlayProps = {
  open: boolean;
  roleLabel: string;
  steps: OnboardingStep[];
  stepIndex: number;
  onNext: () => void;
  onBack: () => void;
  onSkip: () => void;
  onReplay: () => void;
  canReplay: boolean;
  canAdvance: boolean;
  completionHint?: string;
};

export function OnboardingOverlay({
  open,
  roleLabel,
  steps,
  stepIndex,
  onNext,
  onBack,
  onSkip,
  onReplay,
  canReplay,
  canAdvance,
  completionHint,
}: OnboardingOverlayProps) {
  const [anchorRect, setAnchorRect] = useState<DOMRect | null>(null);
  if (!open && !canReplay) return null;
  const step = steps[Math.max(0, Math.min(stepIndex, steps.length - 1))];
  const anchorSelector = useMemo(() => (step ? `#${step.anchorId}` : null), [step]);

  useEffect(() => {
    if (!open || !anchorSelector) {
      setAnchorRect(null);
      return;
    }
    const selector = anchorSelector;

    function refreshAnchor() {
      const element = document.querySelector(selector);
      if (!(element instanceof HTMLElement)) {
        setAnchorRect(null);
        return;
      }
      element.scrollIntoView({ block: "nearest", inline: "nearest" });
      setAnchorRect(element.getBoundingClientRect());
    }

    refreshAnchor();
    window.addEventListener("resize", refreshAnchor);
    window.addEventListener("scroll", refreshAnchor, true);
    return () => {
      window.removeEventListener("resize", refreshAnchor);
      window.removeEventListener("scroll", refreshAnchor, true);
    };
  }, [open, anchorSelector, stepIndex]);

  return (
    <>
      {canReplay && !open && (
        <button className="ux-onboarding-replay" onClick={onReplay}>
          Replay {roleLabel} onboarding
        </button>
      )}
      {open && step && (
        <div className="ux-overlay-backdrop">
          {anchorRect && (
            <div
              className="ux-onboarding-anchor-highlight"
              style={{
                left: Math.max(0, anchorRect.left - 6),
                top: Math.max(0, anchorRect.top - 6),
                width: anchorRect.width + 12,
                height: anchorRect.height + 12,
              }}
            />
          )}
          <div className="ux-overlay-card panel">
            <h3>{roleLabel} onboarding</h3>
            <div className="token-chip">
              Step {stepIndex + 1}/{steps.length}
            </div>
            <h4>{step.title}</h4>
            <p>{step.detail}</p>
            <p className="ux-anchor-hint">
              {anchorRect ? `Highlighted: ${step.anchorId}` : `Anchor not found in current layout: ${step.anchorId}`}
            </p>
            {!canAdvance && completionHint && <p className="ux-anchor-hint">{completionHint}</p>}
            <div className="ux-onboarding-actions">
              <button onClick={onBack} disabled={stepIndex === 0}>
                Back
              </button>
              <button onClick={onSkip}>Skip</button>
              <button onClick={onNext} disabled={!canAdvance}>
                {stepIndex === steps.length - 1 ? "Finish" : "Next"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
