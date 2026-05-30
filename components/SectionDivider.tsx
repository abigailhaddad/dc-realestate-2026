import type { ReactNode } from "react";

export function SectionDivider({
  number,
  title,
  subtitle,
}: {
  number: string;
  title: ReactNode;
  subtitle?: ReactNode;
}) {
  return (
    <div className="flex h-screen w-full flex-col justify-center px-6 sm:px-16 md:px-24">
      <div className="mx-auto w-full max-w-5xl">
        <div className="text-sm font-medium uppercase tracking-[0.18em] mb-6"
             style={{ color: "#D4A03C" /* Warm Gold for "Part N" */ }}>
          Part {number}
        </div>
        <h2 className="text-4xl font-semibold tracking-tight md:text-6xl">{title}</h2>
        {subtitle && <p className="mt-5 max-w-2xl text-xl text-muted-foreground">{subtitle}</p>}
      </div>
    </div>
  );
}
