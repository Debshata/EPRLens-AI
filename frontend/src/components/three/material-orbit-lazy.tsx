"use client";

import dynamic from "next/dynamic";

/** Client-only wrapper: Three.js is loaded lazily and never blocks the page. */
export const MaterialOrbitLazy = dynamic(() => import("./material-orbit").then((m) => m.MaterialOrbit), {
  ssr: false,
  loading: () => <div className="h-[300px] md:h-[450px]" aria-hidden />,
});
