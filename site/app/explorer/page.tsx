import type { Metadata } from "next";
import { Footer, Header } from "../components";
import ExplorerClient, { type EvaluationRow } from "./explorer-client";
import evaluationData from "./evaluation-data.json";

export const metadata: Metadata = {
  title: "Evaluation explorer — HERON",
  description: "Read all 60 model responses and their HERON judge evaluations.",
};

export default function ExplorerPage() {
  return (
    <main>
      <Header />
      <section className="explorer-hero">
        <p className="pilot-label">HERON · Evaluation explorer</p>
        <h1>Read every response and judgment.</h1>
        <p>20 scenarios · 3 models · 60 cross-family judge evaluations</p>
      </section>
      <ExplorerClient rows={evaluationData as EvaluationRow[]} />
      <Footer />
    </main>
  );
}
