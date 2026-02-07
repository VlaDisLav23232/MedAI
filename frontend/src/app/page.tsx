import { Hero } from "@/components/landing/Hero";
import { Features } from "@/components/landing/Features";
import { Architecture } from "@/components/landing/Architecture";
import { Stats } from "@/components/landing/Stats";
import { CTA } from "@/components/landing/CTA";
import { Footer } from "@/components/layout/Footer";

export default function LandingPage() {
  return (
    <main>
      <Hero />
      <Features />
      <Architecture />
      <Stats />
      <CTA />
      <Footer />
    </main>
  );
}
