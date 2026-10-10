import type { Metadata } from "next";
import { CompanyForm } from "@/components/onboarding/company-form";

export const metadata: Metadata = { title: "Company setup — EPRLens AI" };

export default function OnboardingPage() {
  return (
    <main id="main">
      <CompanyForm />
    </main>
  );
}
