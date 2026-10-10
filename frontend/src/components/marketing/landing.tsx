import { ArrowRight, FileSearch, GitCompareArrows, Layers3, LineChart, ScanLine, ShieldCheck, SlidersHorizontal, UploadCloud } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { MaterialOrbitLazy } from "@/components/three/material-orbit-lazy";

const STEPS = [
  { icon: UploadCloud, title: "Upload", text: "Add transaction CSVs, digital invoices and a packaging photo." },
  { icon: GitCompareArrows, title: "Reconcile", text: "Quantities are converted to kg and compared line by line." },
  { icon: Layers3, title: "Visualize", text: "See where packaging mass sits by product, component and material." },
  { icon: SlidersHorizontal, title: "Optimize", text: "Test a lighter pack and see the hypothetical material change." },
];

const FEATURES = [
  { icon: FileSearch, title: "Invoice evidence", text: "Fields are read from digital PDFs with the page and line they came from." },
  { icon: ScanLine, title: "Packaging photo assistant", text: "A probable material with a confidence — never an official EPR category." },
  { icon: ShieldCheck, title: "Traceable findings", text: "Each flag shows the values, the rule and a human review state." },
  { icon: LineChart, title: "Forecast", text: "Next-month packaging mass with the model version and its limits shown." },
];

const PLANS = [
  { name: "Starter", price: "₹2,999", note: "per company / month", points: ["One company", "CSV + invoice reconciliation", "Forecast and simulator"], roadmap: false },
  { name: "Business", price: "₹9,999", note: "per company / month", points: ["Everything in Starter", "Higher upload limits", "Report export (planned)"], roadmap: false },
  { name: "Consultant", price: "₹29,999+", note: "per month, many clients", points: ["Multi-client dashboard", "Document triage", "Not in the current prototype"], roadmap: true },
];

export function Landing() {
  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="bg-grid absolute inset-x-0 top-0 h-[640px] opacity-60" />
        <div className="absolute -top-24 right-0 h-[420px] w-[420px] rounded-full bg-brand opacity-10 blur-[120px]" />
      </div>

      <nav className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 md:px-6" aria-label="Main">
        <Link href="/" className="flex items-center gap-2 font-heading text-lg font-bold">
          <span className="grid size-8 place-items-center rounded-lg border border-brand/50 bg-brand/15 text-brand-bright"><Layers3 className="size-4" aria-hidden /></span>
          EPRLens<span className="text-brand-bright">.AI</span>
        </Link>
        <ul className="hidden items-center gap-6 font-mono text-xs uppercase tracking-wider text-muted md:flex">
          <li><a className="hover:text-fg" href="#how">How it works</a></li>
          <li><a className="hover:text-fg" href="#features">Features</a></li>
          <li><a className="hover:text-fg" href="#pricing">Pricing</a></li>
        </ul>
        <Button asChild size="sm"><Link href="/onboarding?demo=1">Launch demo</Link></Button>
      </nav>

      <header className="mx-auto grid max-w-7xl items-center gap-8 px-4 pb-16 pt-8 md:grid-cols-2 md:px-6 md:pb-24 md:pt-14">
        <div>
          <p className="mb-4 font-mono text-xs uppercase tracking-widest text-brand-bright">Packaging intelligence</p>
          <h1 className="font-heading text-4xl font-bold leading-tight tracking-tight sm:text-5xl md:text-6xl">
            Check your packaging data <span className="text-gradient">before you file</span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-relaxed text-muted md:text-lg">
            Upload records and invoices, spot mismatches, forecast volume and test lighter packaging. Pre-compliance review for producers, importers and brand owners in India.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Button asChild><Link href="/onboarding?demo=1">Explore demo <ArrowRight aria-hidden /></Link></Button>
            <Button asChild variant="outline"><Link href="/onboarding">Set up company</Link></Button>
            <Button asChild variant="ghost"><Link href="/app/review?demo=1&selected=demo-finding-001">View sample finding</Link></Button>
          </div>
          <ul className="mt-8 flex flex-wrap gap-2" aria-label="Principles">
            {["Source linked", "Human reviewed", "Pre-compliance only"].map((t) => <li key={t}><Badge variant="neutral">{t}</Badge></li>)}
          </ul>
        </div>
        <div className="relative">
          <MaterialOrbitLazy />
          <div className="absolute left-0 top-6 rounded-xl border border-white/10 bg-white/[0.04] p-3 backdrop-blur-lg md:left-4">
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted">Illustrative</p>
            <p className="num text-lg font-semibold">0.5 MT vs 500 MT</p>
            <p className="text-xs text-muted">a unit slip a review should catch</p>
          </div>
          <div className="absolute bottom-6 right-0 rounded-xl border border-white/10 bg-white/[0.04] p-3 backdrop-blur-lg md:right-4">
            <p className="font-mono text-[10px] uppercase tracking-wider text-muted">Illustrative</p>
            <p className="num text-lg font-semibold">25 g → 20 g</p>
            <p className="text-xs text-muted">hypothetical pack weight test</p>
          </div>
        </div>
      </header>

      <section id="how" className="border-y border-white/10 bg-surface/60 py-16 md:py-20">
        <div className="mx-auto max-w-7xl px-4 md:px-6">
          <h2 className="font-heading text-2xl font-bold md:text-4xl">How it works</h2>
          <ol className="mt-10 grid gap-6 md:grid-cols-4">
            {STEPS.map((s, i) => (
              <li key={s.title} className="relative rounded-2xl border border-white/10 bg-surface p-6">
                <span className="num absolute right-4 top-4 text-xs text-muted">0{i + 1}</span>
                <s.icon className="mb-4 size-6 text-brand-bright" aria-hidden />
                <h3 className="font-heading text-lg font-semibold">{s.title}</h3>
                <p className="mt-1 text-sm text-muted">{s.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="features" className="mx-auto max-w-7xl px-4 py-16 md:px-6 md:py-24">
        <h2 className="font-heading text-2xl font-bold md:text-4xl">What you get</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((f) => (
            <Card key={f.title} className="transition-all duration-300 hover:-translate-y-1 hover:border-brand/50 hover:shadow-glow-sm">
              <div className="mb-4 grid size-11 place-items-center rounded-lg border border-brand/40 bg-brand/10 text-brand-bright"><f.icon className="size-5" aria-hidden /></div>
              <CardTitle>{f.title}</CardTitle>
              <CardDescription className="mt-2">{f.text}</CardDescription>
            </Card>
          ))}
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-16 md:px-6">
        <Card variant="glass" className="flex flex-col items-start gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="font-heading text-lg font-semibold">Pre-compliance intelligence. Not a CPCB portal, not legal advice.</p>
            <p className="mt-1 text-sm text-muted">Results are decision support for reviewing your own data. Demo screens use clearly labelled synthetic data about fictitious companies.</p>
          </div>
          <Badge variant="synthetic">Synthetic demo data</Badge>
        </Card>
      </section>

      <section id="pricing" className="mx-auto max-w-7xl px-4 pb-20 md:px-6 md:pb-28">
        <h2 className="font-heading text-2xl font-bold md:text-4xl">Pricing concept</h2>
        <p className="mt-2 max-w-2xl text-muted">All prices below are hypothetical placeholders pending approval — there is no checkout.</p>
        <div className="mt-10 grid items-stretch gap-6 md:grid-cols-3">
          {PLANS.map((p) => (
            <Card key={p.name} className={p.name === "Business" ? "border-brand md:scale-105" : "opacity-90"}>
              <div className="flex items-center justify-between"><CardTitle>{p.name}</CardTitle>{p.roadmap && <Badge variant="unknown">Roadmap</Badge>}</div>
              <p className="num mt-4 text-3xl font-bold">{p.price}</p>
              <p className="text-xs text-muted">{p.note}</p>
              <ul className="mt-5 space-y-2 text-sm text-muted">{p.points.map((x) => <li key={x}>• {x}</li>)}</ul>
              <Badge variant="needs_review" className="mt-6">Hypothetical</Badge>
            </Card>
          ))}
        </div>
      </section>

      <footer className="border-t border-white/10 py-8">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 px-4 text-xs text-muted md:flex-row md:justify-between md:px-6">
          <p>© EPRLens AI prototype. Synthetic demo data only; no real company records.</p>
          <p>Decision support — not a CPCB filing, certification or legal advice.</p>
        </div>
      </footer>
    </div>
  );
}
