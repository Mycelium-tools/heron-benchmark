import type { Metadata } from "next";
import Link from "next/link";
import { Footer, Header, Mark } from "../components";

export const metadata: Metadata = {
  title: "HERON launch kit",
  description: "Mock social launch post for the HERON pilot benchmark.",
};

export default function LaunchKit() {
  return (
    <main>
      <Header />
      <section className="launch-shell">
        <div className="launch-intro">
          <p className="eyebrow">Launch kit · mock</p>
          <h1>The post that makes the result legible in ten seconds.</h1>
          <p>Draft social copy and link-card treatment for customer discovery. The language keeps the pilot caveat visible without burying the signal.</p>
        </div>

        <div className="social-stage">
          <article className="tweet-card" aria-label="Mock X post">
            <div className="tweet-author">
              <Mark />
              <p><strong>Sentient Futures</strong><span>@sentientfutures · Aug 4</span></p>
              <b>•••</b>
            </div>
            <div className="tweet-copy">
              <p>Do frontier models give animal welfare proportionate weight—not merely mention it?</p>
              <p>HERON pilot:<br />Luna 74 · Sonnet 68 · Flash 61</p>
              <p>Only 45% of responses were proportionate. On one glue-trap prompt, all three raised welfare; scores still ranged 50–80. Calibration matters.</p>
            </div>
            <div className="tweet-link-card">
              <div className="mini-card-art"><span>HERON</span><strong>How much consideration<br />is enough?</strong></div>
              <div><small>heron · sentient futures</small><strong>Proportionate animal-welfare consideration, measured.</strong><span>20-scenario pilot results</span></div>
            </div>
            <div className="tweet-meta"><span>9:41 AM · Aug 4, 2026</span><span><b>18</b> replies</span><span><b>74</b> reposts</span><span><b>311</b> likes</span></div>
          </article>

          <aside className="post-notes">
            <p className="eyebrow">Why this works</p>
            <div><span>01</span><p><strong>Starts with the construct</strong>The first line explains the benchmark without jargon.</p></div>
            <div><span>02</span><p><strong>Shows the ranking</strong>Three compact numbers make the pilot instantly comparable.</p></div>
            <div><span>03</span><p><strong>Proves the construct</strong>The real example shows why mentioning welfare is not enough.</p></div>
          </aside>
        </div>
        <p className="back-link"><Link href="/">← Back to the benchmark</Link></p>
      </section>
      <Footer />
    </main>
  );
}
