import Link from "next/link";

export function Mark() {
  return <span className="mark" aria-hidden="true">H</span>;
}

export function Header() {
  return (
    <header className="site-header">
      <Link className="brand" href="/"><Mark /><strong>HERON</strong></Link>
      <nav aria-label="Main navigation">
        <Link href="/#results">Results</Link>
        <Link href="/explorer">Explorer</Link>
        <Link href="/#example">Example</Link>
        <Link href="/blog">Pilot note</Link>
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="site-footer">
      <p><strong>HERON</strong> · Hidden-stakes Ethical Reasoning On Nonhumans</p>
      <div><Link href="/explorer">Explorer</Link><Link href="/blog">Pilot note</Link><Link href="/launch">Launch post</Link><a href="mailto:allen@sentientfutures.ai">Contact</a></div>
      <small>Sentient Futures · Pilot release · August 2026</small>
    </footer>
  );
}
