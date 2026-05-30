import type { ReactNode } from "react";
import { Slide, SlideTitle, SlideBody } from "./Deck";

type Layer = {
  name: string;
  path: string;
  fields: string[];
};

export function DataNote({
  vizTitle,
  layers,
  notes,
}: {
  vizTitle: string;
  layers: Layer[];
  notes?: ReactNode;
}) {
  return (
    <Slide>
      <SlideTitle eyebrow="How that was built">{vizTitle} — the data behind it.</SlideTitle>
      <SlideBody>
        <div className="space-y-3 max-w-4xl mt-2">
          {layers.map((l, i) => (
            <div key={i} className="rounded-lg border bg-card p-4">
              <div className="flex items-baseline justify-between gap-3 flex-wrap">
                <div className="font-semibold">{l.name}</div>
                <code className="text-xs text-muted-foreground">{l.path}</code>
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {l.fields.map((f) => (
                  <code
                    key={f}
                    className="px-1.5 py-0.5 rounded bg-muted text-xs font-mono"
                  >
                    {f}
                  </code>
                ))}
              </div>
            </div>
          ))}
        </div>
        {notes && (
          <p className="mt-5 max-w-3xl text-sm text-muted-foreground">{notes}</p>
        )}
      </SlideBody>
    </Slide>
  );
}
