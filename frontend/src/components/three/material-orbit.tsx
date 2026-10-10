"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import type { Group } from "three";
import { TOKENS } from "@/lib/tokens";
import { hasWebGL, prefersReducedMotion } from "./webgl";

/** Static poster: used while loading, without WebGL, and with reduced motion. Illustrative, not data. */
function Poster() {
  return (
    <svg viewBox="0 0 400 400" className="h-full w-full" role="img" aria-label="Illustration: a bottle, a carton and a pouch orbiting a glowing core">
      <defs>
        <radialGradient id="core" cx="50%" cy="50%" r="50%"><stop offset="0" stopColor="#86efac" stopOpacity=".9" /><stop offset="1" stopColor="#166534" stopOpacity=".2" /></radialGradient>
      </defs>
      <ellipse cx="200" cy="200" rx="150" ry="52" fill="none" stroke="#1e293b" strokeWidth="1.5" transform="rotate(-18 200 200)" />
      <ellipse cx="200" cy="200" rx="110" ry="38" fill="none" stroke="#1e293b" strokeWidth="1.5" transform="rotate(24 200 200)" />
      <circle cx="200" cy="200" r="44" fill="url(#core)" stroke="#22c55e" strokeOpacity=".5" />
      <rect x="318" y="146" width="22" height="58" rx="9" fill="#22c55e" fillOpacity=".7" />
      <rect x="55" y="228" width="40" height="34" rx="4" fill="#a8a29e" fillOpacity=".8" />
      <rect x="240" y="300" width="44" height="26" rx="8" fill="#38bdf8" fillOpacity=".7" />
    </svg>
  );
}

function Orbit({ animate }: { animate: boolean }) {
  const outer = useRef<Group>(null);
  const inner = useRef<Group>(null);
  useFrame((_, dt) => {
    if (!animate) return;
    if (outer.current) outer.current.rotation.y += dt * 0.25;
    if (inner.current) inner.current.rotation.y -= dt * 0.4;
  });
  return (
    <>
      <ambientLight intensity={0.8} />
      <pointLight position={[3, 4, 5]} intensity={80} color="#86efac" />
      <mesh>
        <icosahedronGeometry args={[0.9, 1]} />
        <meshStandardMaterial color={TOKENS.brandDark} emissive={TOKENS.brand} emissiveIntensity={0.5} flatShading />
      </mesh>
      <group rotation={[0.3, 0, -0.3]}>
        <group ref={outer}>
          <mesh position={[2.6, 0, 0]}><cylinderGeometry args={[0.28, 0.34, 1.1, 16]} /><meshStandardMaterial color={TOKENS.brand} transparent opacity={0.85} /></mesh>
          <mesh position={[-2.6, 0.2, 0]}><boxGeometry args={[0.8, 0.7, 0.7]} /><meshStandardMaterial color="#a8a29e" /></mesh>
        </group>
      </group>
      <group rotation={[-0.4, 0, 0.35]}>
        <group ref={inner}>
          <mesh position={[1.7, 0, 0]}><boxGeometry args={[0.7, 0.9, 0.12]} /><meshStandardMaterial color={TOKENS.info} transparent opacity={0.85} /></mesh>
        </group>
      </group>
    </>
  );
}

export function MaterialOrbit() {
  const [mode, setMode] = useState<"poster" | "live">("poster");
  const [visible, setVisible] = useState(true);
  const [animate, setAnimate] = useState(false);
  const host = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hasWebGL()) return;
    setAnimate(!prefersReducedMotion());
    setMode("live");
  }, []);

  useEffect(() => {
    const el = host.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([e]) => setVisible(e.isIntersecting));
    io.observe(el);
    const onVis = () => setVisible(!document.hidden);
    document.addEventListener("visibilitychange", onVis);
    return () => { io.disconnect(); document.removeEventListener("visibilitychange", onVis); };
  }, []);

  return (
    <div ref={host} className="relative h-[300px] w-full md:h-[450px]">
      {mode === "live" ? (
        <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 7], fov: 45 }} frameloop={animate && visible ? "always" : "demand"} aria-hidden gl={{ powerPreference: "low-power" }}>
          <Orbit animate={animate && visible} />
        </Canvas>
      ) : <Poster />}
    </div>
  );
}
