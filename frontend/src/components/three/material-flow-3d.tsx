"use client";

import { Line, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useState } from "react";
import { CanvasTexture, LinearFilter } from "three";
import type { FlowLevel, MaterialFlow } from "@/lib/material-flow";
import { MATERIAL_COLORS, TOKENS } from "@/lib/tokens";

const X: Record<FlowLevel, number> = { company: -4.8, product: -1.6, component: 1.6, material: 4.8 };

interface Placed { id: string; level: FlowLevel; label: string; pos: [number, number, number]; r: number; color: string; share: number }

function layout(flow: MaterialFlow): Placed[] {
  const out: Placed[] = [];
  (["company", "product", "component", "material"] as const).forEach((lvl) => {
    const nodes = flow.nodes.filter((n) => n.level === lvl).sort((a, b) => b.kg - a.kg);
    nodes.forEach((n, i) => {
      const y = nodes.length === 1 ? 0 : 3.2 - (6.4 * i) / (nodes.length - 1);
      const mat = n.level === "material" ? MATERIAL_COLORS[n.label] : undefined;
      out.push({
        id: n.id, level: lvl, label: n.label, pos: [X[lvl], y, 0], share: n.share,
        r: 0.14 + 0.55 * Math.sqrt(n.share), // radius derives from the node's real share of the total
        color: mat ?? (lvl === "company" ? TOKENS.brandBright : lvl === "product" ? TOKENS.brand : TOKENS.brandDark),
      });
    });
  });
  return out;
}

/** Text label as a sprite (canvas texture): no DOM roots inside the canvas and no external font files. */
function Label({ text, y, active }: { text: string; y: number; active: boolean }) {
  const { texture, aspect } = useMemo(() => {
    const c = document.createElement("canvas");
    const ctx = c.getContext("2d")!;
    const font = "600 26px ui-monospace, SFMono-Regular, monospace";
    ctx.font = font;
    const w = Math.ceil(ctx.measureText(text).width) + 28;
    c.width = w;
    c.height = 44;
    ctx.font = font;
    ctx.fillStyle = "rgba(0,0,0,0.72)";
    ctx.beginPath();
    ctx.roundRect(0, 0, w, 44, 22);
    ctx.fill();
    ctx.fillStyle = active ? TOKENS.brandBright : "#e2e8f0";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 14, 23);
    const t = new CanvasTexture(c);
    t.minFilter = LinearFilter;
    return { texture: t, aspect: w / 44 };
  }, [text, active]);
  useEffect(() => () => texture.dispose(), [texture]);
  const h = 0.42;
  return (
    <sprite position={[0, y, 0]} scale={[h * aspect, h, 1]}>
      <spriteMaterial map={texture} transparent depthTest={false} />
    </sprite>
  );
}

function Scene({ flow, selected, onSelect }: { flow: MaterialFlow; selected: string | null; onSelect: (id: string) => void }) {
  const placed = useMemo(() => layout(flow), [flow]);
  const byId = useMemo(() => new Map(placed.map((p) => [p.id, p])), [placed]);
  const [hover, setHover] = useState<string | null>(null);
  return (
    <>
      <ambientLight intensity={0.9} />
      <pointLight position={[0, 4, 8]} intensity={60} color="#86efac" />
      {flow.links.map((l) => {
        const a = byId.get(l.from)!, b = byId.get(l.to)!;
        const active = selected && (selected === l.from || selected === l.to);
        return (
          <Line key={`${l.from}>${l.to}`} points={[a.pos, b.pos]} color={active ? TOKENS.brandBright : "#334155"} lineWidth={Math.max(0.6, 5 * Math.sqrt(l.kg / flow.total_kg))} transparent opacity={selected ? (active ? 0.95 : 0.15) : 0.5} />
        );
      })}
      {placed.map((p) => {
        const isSel = selected === p.id;
        const dim = selected && !isSel;
        return (
          <group key={p.id} position={p.pos}>
            <mesh
              onClick={(e) => { e.stopPropagation(); onSelect(p.id); }}
              onPointerOver={(e) => { e.stopPropagation(); setHover(p.id); document.body.style.cursor = "pointer"; }}
              onPointerOut={() => { setHover(null); document.body.style.cursor = ""; }}
            >
              <sphereGeometry args={[p.r, 24, 24]} />
              <meshStandardMaterial color={p.color} emissive={p.color} emissiveIntensity={isSel || hover === p.id ? 0.9 : 0.25} transparent opacity={dim ? 0.35 : 1} roughness={0.4} />
            </mesh>
            {(p.level !== "component" || isSel || hover === p.id) && (
              <Label text={p.label.length > 26 ? `${p.label.slice(0, 24)}…` : p.label} y={-(p.r + 0.35)} active={isSel} />
            )}
          </group>
        );
      })}
      {/* manual orbit only (no autorotate): reduced-motion friendly */}
      <OrbitControls enablePan={false} enableZoom={false} enableDamping={false} minAzimuthAngle={-0.7} maxAzimuthAngle={0.7} minPolarAngle={1.1} maxPolarAngle={2.0} />
    </>
  );
}

export default function MaterialFlow3D({ flow, selected, onSelect }: { flow: MaterialFlow; selected: string | null; onSelect: (id: string) => void }) {
  return (
    <div className="h-[360px] w-full overflow-hidden rounded-2xl border border-white/10 bg-black/40 md:h-[440px]" data-testid="material-flow-3d">
      <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 12.5], fov: 45 }} frameloop="demand" gl={{ antialias: true, powerPreference: "low-power" }} aria-hidden>
        <Scene flow={flow} selected={selected} onSelect={onSelect} />
      </Canvas>
    </div>
  );
}
