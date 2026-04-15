import type { Tutorial } from "../types";

type Props = {
  tutorial: Tutorial | null;
};

export function TutorialPanel({ tutorial }: Props) {
  return (
    <div className="panel side-panel">
      <h3>DM Tutorial</h3>
      {!tutorial ? (
        <div>Loading tutorial...</div>
      ) : (
        <>
          <div style={{ marginBottom: 6 }}>
            <strong>{tutorial.title}</strong> ({tutorial.estimated_minutes} min)
          </div>
          <ol className="list">
            {tutorial.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </>
      )}
    </div>
  );
}
