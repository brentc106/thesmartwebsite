'use client';

import { useState, useEffect, useRef } from 'react';

const PAIN_POINTS = [
  "My website is embarrassing but I don't know where to start",
  "I know I'm losing leads but I don't know how many",
  "I've been quoted $5,000+ and I just need something that works",
  "Customers can't find me on Google",
  "My phone doesn't ring like it used to",
  "I built it myself years ago and it shows",
];

const HOW_IT_WORKS = [
  { num: '01', title: 'We audit your business (free)', body: "We scan your website, Google profile, and local competitors. Full breakdown. No charge.", icon: '🔍' },
  { num: '02', title: 'We build your mockup (free)', body: "See your new site before paying a cent. You review, we refine.", icon: '🎨' },
  { num: '03', title: 'We launch it ($497)', body: "Live within 14 days. Guaranteed. $99/mo hosting after that.", icon: '🚀' },
];

const PRICING_TIERS = [
  { name: 'Starter', price: '$497', monthly: '$99/mo', includes: ['Website rebuild', 'Mobile-first design', 'Hosting included', '14-day delivery'], popular: false },
  { name: 'Growth ⭐', price: '$797', monthly: '$197/mo', includes: ['Everything in Starter', 'AI Chatbot', 'Lead qualification', '24/7 enquiry capture'], popular: true },
  { name: 'Premium', price: '$1,497', monthly: '$397/mo', includes: ['Everything in Growth', 'AI Receptionist', 'Call routing', 'SMS follow-ups'], popular: false },
  { name: 'Full Stack', price: '$2,497', monthly: '$597/mo', includes: ['Everything in Premium', 'Lead automation', 'Review requests', 'Quote follow-ups'], popular: false },
];

const AI_SERVICES = [
  { title: 'AI Chatbot', body: "Captures enquiries 24/7. Answers questions, qualifies leads, books jobs.", price: 'from $797' },
  { title: 'AI Receptionist', body: "Never miss a call. Answers, qualifies, books jobs while you're on the tools.", price: 'from $1,497' },
  { title: 'Lead Automation', body: "Quote follow-ups, review requests, missed-call texts. All automatic.", price: 'from $2,497' },
];



const PROBLEM_OPTIONS = [
  { value: 'not-enough-leads', label: 'Not enough leads coming in' },
  { value: 'cant-find-google', label: "Can't be found on Google" },
  { value: 'outdated', label: 'Website looks outdated or embarrassing' },
  { value: 'no-website', label: "I don't have a website yet" },
  { value: 'losing-calls', label: "I'm losing calls I don't know about" },
];

const GLOBAL_CSS = `
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  ::selection { background: #B8FF00; color: #080808; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #080808; }
  ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
  input:focus, select:focus, textarea:focus { border-color: #B8FF00 !important; outline: none; }
  h1, h2, h3, h4 { font-family: 'Montserrat', sans-serif; font-weight: 900; text-transform: uppercase; letter-spacing: -0.03em; }
  body, p, li { font-family: 'IBM Plex Sans', sans-serif; }
  nav, button, input, select, label, .mono { font-family: 'IBM Plex Mono', monospace; }
  .nav-links a { font-family: 'IBM Plex Mono', monospace !important; font-weight: 400; text-transform: uppercase; letter-spacing: 0.08em; }
  .step-icon { width: 64px; height: 64px; border-radius: 50%; border: 2px solid #B8FF00; background: #0F0F0F; display: flex; align-items: center; justify-content: center; font-size: 28px; flex-shrink: 0; box-shadow: 0 0 20px rgba(184,255,0,0.1); }
  .signal-tick { color: #B8FF00; font-weight: bold; }
  .hamburger { display: none; flex-direction: column; gap: 5px; background: none; border: none; cursor: pointer; padding: 8px; }
  .hamburger span { width: 22px; height: 2px; background: #F2F2F2; display: block; transition: all 0.25s; }
  .mobile-menu { display: none; position: fixed; inset: 0; top: 58px; background: #080808; z-index: 99; flex-direction: column; align-items: center; justify-content: center; gap: 36px; border-top: 1px solid #1E1E1E; }
  .mobile-menu.open { display: flex; }
  .mobile-menu a { font-family: 'IBM Plex Mono', monospace; font-size: 18px; color: #F2F2F2; text-decoration: none; text-align: center; }
  .mobile-menu .btn-primary { background: #B8FF00; color: #080808; font-weight: 900; padding: 14px 32px; border-radius: 8px; text-transform: uppercase; letter-spacing: 0.05em; font-size: 14px; font-family: 'IBM Plex Mono', monospace; }
  @media (max-width: 768px) {
  .hamburger { display: none !important; }
  .nav-inner { height: auto !important; padding: 10px 0; }
  .nav-links { display: flex !important; width: 100%; gap: 16px; padding-top: 10px; border-top: 1px solid #1a1a1a; justify-content: flex-start; align-items: center; }
  .nav-links a { font-size: 10px !important; }
  .nav-links .shimmer-cta.primary { margin-left: auto; padding: 6px 12px !important; font-size: 10px !important; font-weight: 700 !important; box-shadow: none !important; }
}
  .glow-card { transition: all 0.3s ease; }
  .glow-card:hover { box-shadow: 0 0 32px rgba(184,255,0,0.12); transform: translateY(-2px); }
  .nav-scrolled { backdrop-filter: blur(12px); background: rgba(8,8,8,0.9) !important; border-color: #1E1E1E !important; }
  .shimmer-cta { display: inline-block; padding: 14px 28px; border-radius: 8px; font-weight: 700; font-size: 14px; text-decoration: none; font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.05em; transition: all 0.15s ease; }
  .shimmer-cta.primary { background: #B8FF00; color: #080808; box-shadow: 0 0 32px rgba(184,255,0,0.3); }
  .shimmer-cta.ghost { background: transparent; color: #F2F2F2; border: 1px solid #333; }
  .shimmer-cta:hover { transform: translateY(-1px); }
  @keyframes auditGlow { 0%,100%{box-shadow:0 0 20px rgba(184,255,0,0.05);border-color:#2a2a2a} 50%{box-shadow:0 0 48px rgba(184,255,0,0.2);border-color:#B8FF00} }
  .gradient-text { background: linear-gradient(135deg, #B8FF00 0%, #ffffff 40%, #B8FF00 60%, #ffffff 100%); background-size: 200% auto; -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
`;

function Reveal({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { setVis(true); obs.disconnect(); } }, { threshold: 0.1 });
    if (ref.current) obs.observe(ref.current);
    return () => obs.disconnect();
  }, []);
  return (
    <div ref={ref} style={{
      opacity: vis ? 1 : 0, transform: vis ? 'none' : 'translateY(20px)',
      transition: `opacity 0.55s ease ${delay}ms, transform 0.55s ease ${delay}ms`,
    }}>
      {children}
    </div>
  );
}

function GlowCard({ children }: { children: React.ReactNode }) {
  const [h, setH] = useState(false);
  return (
    <div className="glow-card" onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{ background: '#0F0F0F', border: `1px solid ${h ? '#B8FF00' : '#1E1E1E'}`, borderRadius: 12, padding: '28px 24px', position: 'relative', overflow: 'hidden' }}>
      {children}
    </div>
  );
}

function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40);
    window.addEventListener('scroll', onScroll, { passive: true });
    const btn = document.getElementById('hamburger');
    if (btn) btn.addEventListener('click', () => setMenuOpen(v => !v));
    document.querySelectorAll('.mobile-menu a').forEach(a => a.addEventListener('click', () => setMenuOpen(false)));
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <>
      <nav className={scrolled ? 'nav-scrolled' : ''} style={{ position: 'sticky', top: 0, zIndex: 100, background: 'rgba(8,8,8,0.92)', borderBottom: '1px solid #1a1a1a', padding: '0 16px', transition: 'all 0.3s ease' }}>
        <div className="nav-inner" style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: 58, flexWrap: 'wrap', gap: 8 }}>
          <span style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.02em', fontSize: 15, color: '#F2F2F2' }}>
            The<span style={{ color: '#B8FF00' }}>Smart</span>Website.co
          </span>
          <div className="nav-links" style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
            <a href="#how" style={{ color: '#AAAAAA', textDecoration: 'none', fontSize: 13 }}>How it works</a>
            <a href="#pricing" style={{ color: '#AAAAAA', textDecoration: 'none', fontSize: 13 }}>Pricing</a>
            <a href="#audit" style={{ color: '#AAAAAA', textDecoration: 'none', fontSize: 13 }}>Contact</a>
            <a href="#audit" className="shimmer-cta primary">Free audit →</a>
          </div>
          <button id="hamburger" className="hamburger" aria-label="Open menu">
            <span /><span /><span />
          </button>
        </div>
      </nav>
      <div id="mobile-menu" className={`mobile-menu${menuOpen ? ' open' : ''}`}>
        <a href="#how">How it works</a>
        <a href="#pricing">Pricing</a>
        <a href="#audit">Contact</a>
        <a href="#audit" className="btn-primary">Get free audit →</a>
      </div>
    </>
  );
}

interface FormState { name: string; businessName: string; phone: string; website: string; suburb: string; biggestProblem: string; anythingElse: string; email: string; }
function AuditForm() {
  const [form, setForm] = useState<FormState>({ name: '', businessName: '', phone: '', website: '', suburb: '', biggestProblem: '', anythingElse: '', email: '' });
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [err, setErr] = useState('');
  const set = (k: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setForm(f => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setStatus('loading'); setErr('');
    try {
      const res = await fetch('/api/contact', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) });
      const d = await res.json();
      if (d.success) setStatus('success'); else { setStatus('error'); setErr(d.error || 'Something went wrong.'); }
    } catch { setStatus('error'); setErr('Network error.'); }
  };

  if (status === 'success') return (
    <div style={{ background: '#0F0F0F', border: '1px solid #1E1E1E', borderRadius: 16, padding: '48px 32px', textAlign: 'center', maxWidth: 520, margin: '0 auto' }}>
      <div style={{ fontSize: 56, marginBottom: 16, color: '#B8FF00' }}>✓</div>
      <h3 style={{ color: '#B8FF00', fontSize: 24, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.02em', marginBottom: 12 }}>You&apos;re in the queue.</h3>
      <p style={{ color: '#888', fontSize: 16, lineHeight: 1.6 }}>Your audit is being put together now. Check your inbox within 2 hours.</p>
    </div>
  );

  const inp: React.CSSProperties = { width: '100%', padding: '15px 16px', borderRadius: 8, border: '1px solid #1E1E1E', background: '#0F0F0F', color: '#F2F2F2', fontSize: 15, fontFamily: "'IBM Plex Mono', monospace", boxSizing: 'border-box', outline: 'none', transition: 'border-color 0.15s' };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 520, margin: '0 auto' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {[
          { k: 'name' as keyof FormState, p: 'Your name *', t: 'text', req: true },
          { k: 'businessName' as keyof FormState, p: 'Business name *', t: 'text', req: true },
          { k: 'phone' as keyof FormState, p: 'Mobile * (e.g. 0412 345 678)', t: 'tel', req: true },
          { k: 'email' as keyof FormState, p: 'Email address *', t: 'email', req: true },
          { k: 'website' as keyof FormState, p: 'Website URL *', t: 'url', req: false },
          { k: 'suburb' as keyof FormState, p: 'Suburb / Location *', t: 'text', req: true },
        ].map(f => (
          <input key={f.k} type={f.t} placeholder={f.p} required={f.req} value={form[f.k]} onChange={set(f.k)} style={inp} />
        ))}
        <select required value={form.biggestProblem} onChange={set('biggestProblem')} style={{ ...inp, appearance: 'none', cursor: 'pointer', color: form.biggestProblem ? '#F2F2F2' : '#666' }}>
          <option value="" disabled selected>What&apos;s your biggest problem right now? *</option>
          {PROBLEM_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <textarea placeholder="Anything else? (optional)" rows={3} value={form.anythingElse} onChange={set('anythingElse')} style={{ ...inp, resize: 'vertical', minHeight: 80 }} />
        <button type="submit" disabled={status === 'loading'} style={{ background: '#B8FF00', color: '#080808', border: 'none', padding: '18px 32px', borderRadius: 10, fontWeight: 700, fontSize: 16, cursor: status === 'loading' ? 'not-allowed' : 'pointer', fontFamily: "'IBM Plex Mono', monospace", textTransform: 'uppercase', letterSpacing: '0.05em', opacity: status === 'loading' ? 0.7 : 1 }}>
          {status === 'loading' ? 'Sending...' : 'Build my free audit →'}
        </button>
        {status === 'error' && err && <p style={{ color: '#FF5C1A', fontSize: 14, textAlign: 'center', margin: 0, fontFamily: "'IBM Plex Mono', monospace" }}>{err}</p>}
        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', justifyContent: 'center', fontSize: 12, color: '#555', fontFamily: "'IBM Plex Mono', monospace" }}>
          <span><span className="signal-tick">✓</span> Free to start</span>
          <span><span className="signal-tick">✓</span> No credit card</span>
          <span><span className="signal-tick">✓</span> Only pay if you love it</span>
        </div>
      </div>
    </form>
  );
}

export default function HomePage() {
  return (
    <>
      <style>{GLOBAL_CSS}</style>
      <Nav />

      {/* HERO */}
      <section style={{ padding: '80px 16px', background: '#080808' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 56, alignItems: 'center' }}>
            <div>
              <Reveal>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
                  <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#B8FF00', animation: 'pulse 2s ease infinite' }} />
                  <span style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.12em', color: '#B8FF00' }}>Free Website Audit</span>
                </div>
                <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}`}</style>
                <h1 style={{ fontSize: 'clamp(42px,9vw,88px)', fontWeight: 900, lineHeight: 0.92, letterSpacing: '-0.03em', marginBottom: 20, color: '#F2F2F2', textTransform: 'uppercase' }}>
                  Your website<br />
                  <span className="gradient-text">is costing you jobs.</span>
                </h1>
                <p style={{ fontSize: 18, color: '#BBBBBB', lineHeight: 1.6, marginBottom: 28, maxWidth: 480 }}>
                  We audit your site for free — show you exactly what it's costing you — then fix it for $497.
                </p>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 40 }}>
                  <a href="#audit" className="shimmer-cta primary">Get my free audit →</a>
                  <a href="#how" className="shimmer-cta ghost">See how it works ↓</a>
                </div>
                <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap', paddingTop: 32, borderTop: '1px solid #1E1E1E' }}>
                  {[['$0', 'free audit, no strings'], ['14-day', 'delivery guarantee'], ['100%', 'pay only if you love it']].map(([n, l]) => (
                    <div key={l as string}>
                      <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, fontSize: 20, color: '#B8FF00', textTransform: 'uppercase' }}>{n}</div>
                      <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#666', marginTop: 2 }}>{l}</div>
                    </div>
                  ))}
                </div>
              </Reveal>
            </div>
            <Reveal delay={150}>
 <div style={{ background: '#0F0F0F', border: '1px solid #2a2a2a', borderRadius: 16, padding: 32, position: 'relative', overflow: 'hidden', maxWidth: 400, animation: 'auditGlow 3s ease-in-out infinite' }}>
 <div style={{ position: 'absolute', top: 16, right: 16, fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: '#777', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Audit Preview</div>
 <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: '#555', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8 }}>Site Health Score</div>
 <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, fontSize: 80, lineHeight: 1, color: '#888', letterSpacing: '-0.04em' }}>
 18<span style={{ color: '#555' }}>/30</span>
 </div>
 <div style={{ display: 'inline-block', marginTop: 10, marginBottom: 20, padding: '3px 10px', borderRadius: 4, background: 'rgba(255,60,60,0.1)', border: '1px solid rgba(255,60,60,0.25)', fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#FF4444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
 ● Critical
 </div>
 <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 10, color: '#444', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>
 Showing 3 of 11 issues found
 </div>
 <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
 {['Mobile experience poor', 'Slow load times (8.2s)', 'No trust signals found'].map(issue => (
 <div key={issue} style={{ display: 'flex', gap: 8, alignItems: 'center', fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: '#CCCCCC' }}>
 <span style={{ color: '#FF4444', fontSize: 14, flexShrink: 0 }}>✗</span> {issue}
 </div>
 ))}
 </div>
 <div style={{ position: 'relative', marginBottom: 4 }}>
 {[72, 55, 85].map((w, i) => (
 <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8, filter: 'blur(3px)', opacity: 0.35 }}>
 <span style={{ color: '#FF4444', fontSize: 14, flexShrink: 0 }}>✗</span>
 <div style={{ height: 11, borderRadius: 4, background: '#2a2a2a', width: `${w}%` }} />
 </div>
 ))}
 <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(to bottom, transparent 10%, #0F0F0F 90%)' }} />
 </div>
 <div style={{ marginTop: 16, padding: '10px 16px', borderRadius: 100, background: 'rgba(184,255,0,0.08)', display: 'inline-flex', gap: 8, fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#B8FF00' }}>
 ≈ ~$12,750/month in missed leads
 </div>
 <div style={{ marginTop: 16 }}>
 <a href="#audit" style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#B8FF00', textDecoration: 'none', opacity: 0.8 }}>
 Get your full report free →
 </a>
 </div>
 </div>
 </Reveal>
          </div>
        </div>
      </section>

      {/* MARQUEE */}
      <div style={{ borderTop: '1px solid #1E1E1E', borderBottom: '1px solid #1E1E1E', overflow: 'hidden', padding: '14px 0', background: '#080808' }}>
        <div style={{ display: 'flex', whiteSpace: 'nowrap', animation: 'marquee 30s linear infinite' }}>
          {['Plumbers', 'Electricians', 'Builders', 'Painters', 'Landscapers', 'Cleaners', 'Mechanics', 'Cafes', 'Salons', 'Physios', 'Tradies'].map(t => (
            <span key={t} style={{ padding: '0 32px', fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#444', textTransform: 'uppercase', letterSpacing: '0.1em' }}>{t} · </span>
          ))}
        </div>
        <style>{`@keyframes marquee{0%{transform:translateX(0)}100%{transform:translateX(-50%)}}`}</style>
      </div>

      {/* PAIN POINTS */}
      <section style={{ padding: '80px 16px', background: '#0A0A0A' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <Reveal><p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#B8FF00', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 8 }}>Sound familiar?</p></Reveal>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 10, marginTop: 32 }}>
            {PAIN_POINTS.map((p, i) => (
              <Reveal key={p} delay={i * 60}>
                <GlowCard>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', fontSize: 14, lineHeight: 1.5, color: '#CCCCCC' }}>
                    <span style={{ color: '#B8FF00', flexShrink: 0, marginTop: 2, fontSize: 16 }}>→</span>{p}
                  </div>
                </GlowCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section id="how" style={{ padding: '80px 16px', background: '#080808' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <Reveal>
            <p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#B8FF00', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 8 }}>Three steps. No fluff.</p>
            <h2 style={{ fontSize: 'clamp(32px,6vw,56px)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.03em', marginBottom: 56, color: '#F2F2F2' }}>How it works</h2>
          </Reveal>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 48 }}>
            {HOW_IT_WORKS.map((s, i) => (
              <Reveal key={s.num} delay={i * 80}>
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: 20 }}>
                  <div className="step-icon">{s.icon}</div>
                  <div>
                    <h3 style={{ fontSize: 15, fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.01em', marginBottom: 10, color: '#F2F2F2' }}>{s.title}</h3>
                    <p style={{ color: '#AAAAAA', lineHeight: 1.7, fontSize: 14 }}>{s.body}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" style={{ padding: '80px 16px', background: '#0A0A0A' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <Reveal>
            <p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#B8FF00', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 8, textAlign: 'center' }}>Simple pricing. No surprises.</p>
            <h2 style={{ fontSize: 'clamp(32px,6vw,56px)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.03em', marginBottom: 48, color: '#F2F2F2', textAlign: 'center' }}>Choose your plan</h2>
          </Reveal>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
            {PRICING_TIERS.map((t, i) => (
              <Reveal key={t.name} delay={i * 70}>
                <GlowCard>
                  {t.popular && (
                    <div style={{ position: 'absolute', top: -1, right: 20, background: '#B8FF00', color: '#080808', fontSize: 10, fontWeight: 700, padding: '3px 10px', borderRadius: '0 0 6px 6px', fontFamily: "'IBM Plex Mono', monospace", letterSpacing: '0.05em', textTransform: 'uppercase' }}>Most Popular</div>
                  )}
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#666', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>{t.name}</div>
                  <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, fontSize: 40, lineHeight: 1, marginBottom: 4, color: '#F2F2F2', letterSpacing: '-0.03em' }}>{t.price}</div>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: '#B8FF00', marginBottom: 16 }}>{t.monthly}</div>
                  <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {t.includes.map(f => (
                      <li key={f} style={{ display: 'flex', gap: 8, alignItems: 'center', fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#BBBBBB' }}>
                        <span className="signal-tick">✓</span> {f}
                      </li>
                    ))}
                  </ul>
                </GlowCard>
              </Reveal>
            ))}
          </div>
          <Reveal>
            <p style={{ textAlign: 'center', marginTop: 36, color: '#555', fontSize: 14 }}>
              <span className="signal-tick">✓</span> 14-day delivery guarantee — not live in 14 days, full refund.
            </p>
          </Reveal>
        </div>
      </section>

      {/* AUDIT DATA */}
      <section style={{ padding: '80px 16px', background: '#080808' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <Reveal>
            <p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#B8FF00', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 8 }}>What the data shows</p>
            <h2 style={{ fontSize: 'clamp(32px,6vw,56px)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.03em', marginBottom: 16, color: '#F2F2F2' }}>We've reviewed hundreds<br />of tradie websites.<br />Same problems. Every time.</h2>
            <p style={{ fontSize: 16, color: '#AAAAAA', marginBottom: 48, maxWidth: 520 }}>Australian tradie and small business websites share the same issues. Here's what consistently costs you the most.</p>
          </Reveal>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
            {[
              { stat: '4 in 5', label: "Sites have no clear primary CTA", detail: "Visitors don't know where to click — so they leave." },
              { stat: '$8,400', label: 'Average monthly opportunity found', detail: 'Revenue sitting on the table before a single change is made.' },
              { stat: '16/30', label: 'Average website health score', detail: 'Most tradie sites land in the Critical range. The benchmark to beat is 26.' },
            ].map((item, i) => (
              <Reveal key={item.label} delay={i * 80}>
                <GlowCard>
                  <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, fontSize: 52, color: '#B8FF00', letterSpacing: '-0.03em', lineHeight: 1, marginBottom: 14 }}>{item.stat}</div>
                  <div style={{ fontSize: 15, fontWeight: 600, color: '#F2F2F2', marginBottom: 8 }}>{item.label}</div>
                  <p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#666', lineHeight: 1.6, margin: 0 }}>{item.detail}</p>
                </GlowCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* AI SERVICES */}
      <section style={{ padding: '80px 16px', background: '#0A0A0A' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <Reveal><p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#B8FF00', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 8 }}>We do more than websites</p></Reveal>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginTop: 32 }}>
            {AI_SERVICES.map((a, i) => (
              <Reveal key={a.title} delay={i * 70}>
                <div style={{ background: '#0F0F0F', border: '1px solid #1E1E1E', borderRadius: 12, padding: '28px 24px' }}>
                  <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, fontSize: 16, textTransform: 'uppercase', letterSpacing: '-0.01em', marginBottom: 10, color: '#F2F2F2' }}>{a.title}</div>
                  <p style={{ color: '#AAAAAA', lineHeight: 1.7, fontSize: 14, marginBottom: 16 }}>{a.body}</p>
                  <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 13, color: '#B8FF00' }}>{a.price}</div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* GUARANTEE */}
      <section style={{ padding: '80px 16px', background: '#0A0A0A' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <Reveal>
            <p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 11, color: '#B8FF00', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 8 }}>Zero risk. Seriously.</p>
            <h2 style={{ fontSize: 'clamp(32px,6vw,56px)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.03em', marginBottom: 56, color: '#F2F2F2' }}>Why this is<br />a no-brainer</h2>
          </Reveal>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
            {[
              { icon: '🎨', title: 'See it before you pay', body: "We build your new site as a free mockup first. You approve the design before we go live. Hate it? Walk away — no invoice." },
              { icon: '🚀', title: 'Live in 14 days. Guaranteed.', body: "Not live within 14 days of you signing off? You pay nothing. No exceptions, no fine print, no excuses." },
              { icon: '💚', title: 'Only pay if you love it', body: "We only invoice when you're genuinely happy with what we built. No deposit, no contract, no risk on your end." },
            ].map((item, i) => (
              <Reveal key={item.title} delay={i * 80}>
                <GlowCard>
                  <div style={{ fontSize: 36, marginBottom: 16 }}>{item.icon}</div>
                  <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, fontSize: 15, textTransform: 'uppercase', letterSpacing: '-0.01em', marginBottom: 10, color: '#F2F2F2' }}>{item.title}</div>
                  <p style={{ color: '#AAAAAA', lineHeight: 1.7, fontSize: 14, margin: 0 }}>{item.body}</p>
                </GlowCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* AUDIT FORM */}
      <section id="audit" style={{ padding: '100px 16px', background: '#080808' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto', textAlign: 'center' }}>
          <Reveal>
            <h2 style={{ fontSize: 'clamp(32px,7vw,56px)', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.03em', marginBottom: 16, color: '#F2F2F2' }}>
              Get your free audit.<br />
              <span className="gradient-text">See what you&apos;re missing.</span>
            </h2>
            <p style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#B8FF00', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 32, fontWeight: 700 }}>&#9679; We only take on 3 rebuilds per week — spots fill fast</p>
            <p style={{ fontSize: 18, color: '#AAAAAA', marginBottom: 48 }}>Free to start. Only pay if you love what we build.</p>
          </Reveal>
          <Reveal delay={100}><AuditForm /></Reveal>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ padding: '40px 16px', borderTop: '1px solid #1E1E1E', background: '#080808' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 20, marginBottom: 32 }}>
            <div>
              <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 900, textTransform: 'uppercase', letterSpacing: '-0.02em', fontSize: 15, marginBottom: 4, color: '#F2F2F2' }}>The<span style={{ color: '#B8FF00' }}>Smart</span>Website.co</div>
              <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontSize: 12, color: '#444' }}>Websites and AI for Australian businesses</div>
            </div>
            <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
              <a href="#pricing" style={{ color: '#444', textDecoration: 'none', fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>Pricing</a>
              <a href="#how" style={{ color: '#444', textDecoration: 'none', fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>How it works</a>
              <a href="#audit" style={{ color: '#444', textDecoration: 'none', fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>Contact</a>
            </div>
          </div>
          <div style={{ borderTop: '1px solid #1E1E1E', paddingTop: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
            <a href="mailto:hello@thesmartwebsite.co" style={{ color: '#666', textDecoration: 'none', fontSize: 13, fontFamily: "'IBM Plex Mono', monospace" }}>hello@thesmartwebsite.co</a>
            <div style={{ color: '#333', fontSize: 12, fontFamily: "'IBM Plex Mono', monospace" }}>© 2026 The Smart Website Co.</div>
          </div>
        </div>
      </footer>
    </>
  );
}
