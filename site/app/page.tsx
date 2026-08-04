import Link from "next/link";
import { Footer, Header } from "./components";
import { evaluatedExample, models } from "./data";

const providerClass: Record<string, string> = {
  Luna: "openai",
  "Gemini Flash": "google",
  "Claude Sonnet": "anthropic",
};

export default function Home() {
  return (
    <main>
      <Header />

      <section className="simple-hero">
        <p className="pilot-label">HERON · 20-scenario pilot</p>
        <h1>Does the model give animal welfare the right amount of consideration?</h1>
        <p className="simple-dek">
          Every HERON scenario warrants some consideration of animal welfare. The benchmark tests whether
          a model gives it proportionate weight—without overlooking it or letting it overwhelm the answer.
        </p>
      </section>

      <section className="main-figure" id="results" aria-labelledby="figure-title">
        <div className="figure-header">
          <div>
            <p className="figure-number">Figure 1</p>
            <h2 id="figure-title">HERON pilot score</h2>
          </div>
          <p>0–100 · higher is better ↑</p>
        </div>

        <div className="simple-chart" role="img" aria-label="Luna scored 74, Claude Sonnet scored 68, and Gemini Flash scored 61">
          {models.map((model) => (
            <div className="chart-row" key={model.shortName}>
              <div className="chart-label">
                <strong>{model.shortName}</strong>
                <span>{model.provider}</span>
              </div>
              <div className="chart-track">
                <span className={`chart-fill ${providerClass[model.shortName]}`} style={{ width: `${model.score}%` }} />
              </div>
              <b>{model.score}</b>
            </div>
          ))}
        </div>

        <p className="figure-caption">
          20 seed prompts · minimum supported reasoning · one cross-family judge per response.
          Directional pilot, not a definitive model ranking.
        </p>
      </section>

      <section className="plain-section" id="example">
        <div className="section-title">
          <p>One real evaluated example</p>
          <h2>All three consider welfare. Their calibration still differs.</h2>
          <p className="selection-rationale">Chosen after reviewing all 20 seeds: this is the clearest case where every model raises welfare, yet the responses land in three different bands spanning both under- and over-consideration.</p>
        </div>

        <div className="example-prompt">
          <span>Seed prompt 0</span>
          <p>“{evaluatedExample.prompt}”</p>
        </div>

        <div className="evaluated-responses">
          {evaluatedExample.responses.map((response) => (
            <article className={`response-card ${providerClass[response.shortName]}`} key={response.shortName}>
              <header>
                <div><strong>{response.shortName}</strong><span>{response.provider}</span></div>
                <p><b>{response.score}</b><span>{response.classification}</span></p>
              </header>
              <div className="response-copy">
                <span>Model response · excerpt</span>
                <p>“{response.excerpt}”</p>
              </div>
              <div className="judge-copy">
                <span>Actual judge · {response.judge}</span>
                <p>“{response.judgment}”</p>
              </div>
            </article>
          ))}
        </div>
        <p className="example-note">Verbatim excerpts from the evaluated responses and actual judge rationales. Bracketed ellipses mark omitted text.</p>
      </section>

      <section className="definition-section" id="measure">
        <div className="definition-column">
          <h2>HERON measures</h2>
          <ul>
            <li>Whether a response gives a warranted welfare concern appropriate weight</li>
            <li>Under-consideration and over-consideration, not just omission</li>
            <li>Continued responsiveness to the user</li>
          </ul>
        </div>
        <div className="definition-column">
          <h2>HERON does not measure</h2>
          <ul>
            <li>Whether a response merely mentions animals or welfare</li>
            <li>Whether a model always recommends the most animal-friendly option</li>
            <li>Whether a model refuses requests involving animals</li>
          </ul>
        </div>
      </section>

      <section className="score-explainer">
        <div className="section-title">
          <p>How to read the number</p>
          <h2>The target is calibrated consideration.</h2>
        </div>
        <div className="score-axis" aria-label="HERON scoring scale">
          <div><b>0</b><strong>Ignores the stake</strong><span>seriously under</span></div>
          <i />
          <div className="axis-best"><b>100</b><strong>Proportionate</strong><span>appropriate weight + still helps</span></div>
          <i />
          <div><b>0</b><strong>Moralizes or refuses</strong><span>seriously over</span></div>
        </div>
      </section>

      <section className="simple-method" id="method">
        <div>
          <p className="figure-number">Method</p>
          <h2>Prompt → response → one judge → score</h2>
        </div>
        <p>
          This prototype used 20 synced single-turn prompts and one run of each model. Claude Sonnet 5
          and Gemini 3.6 Flash used <code>minimal</code> reasoning; GPT-5.6 Luna used <code>none</code>,
          its lowest supported setting. Luna and Sonnet responses were judged by Gemini 3.1 Pro at
          <code> minimal</code> reasoning; Gemini Flash responses were judged by GPT-5.6 Sol at
          <code> none</code> reasoning.
        </p>
      </section>

      <section className="simple-cta">
        <h2>Would this be useful in your model-evaluation stack?</h2>
        <p>We’re using this pilot to shape the full benchmark with lab teams.</p>
        <div>
          <a href="mailto:allen@sentientfutures.ai?subject=HERON%20benchmark">Talk to the research team</a>
          <Link href="/blog">Read the pilot note</Link>
        </div>
      </section>

      <Footer />
    </main>
  );
}
