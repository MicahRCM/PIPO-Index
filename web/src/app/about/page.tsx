import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";
import headshot from "./dan-myers.jpg";

export const metadata: Metadata = {
  title: "About — PIPO Index",
  description:
    "The PIPO Index is led by Dan Myers, 15th President of Misericordia University, whose work on student persistence shapes the project.",
};

// Credentials strip — mirrors the homepage "facts band" so the two pages
// read as one system.
const MARKS = [
  { n: "15th", l: "president, Misericordia" },
  { n: "17", l: "years at Notre Dame" },
  { n: "8", l: "books published" },
  { n: "60+", l: "articles published" },
];

export default function About() {
  return (
    <>
      {/* ── Header ───────────────────────────────────────────── */}
      <section className="border-b border-rule">
        <div className="mx-auto w-full max-w-7xl px-6 pb-14 pt-20 sm:pt-24">
          <p
            className="reveal font-mono text-[11px] uppercase tracking-[0.34em] text-ink-soft"
            style={{ animationDelay: "0.05s" }}
          >
            About
          </p>
          <h1
            className="reveal mt-6 font-display text-5xl font-semibold leading-[0.95] tracking-tight sm:text-7xl"
            style={{ animationDelay: "0.12s" }}
          >
            The people behind
            <br />
            the <span className="italic text-teal">index</span>.
          </h1>
          <p
            className="reveal mt-8 max-w-2xl text-lg leading-relaxed text-ink-soft"
            style={{ animationDelay: "0.24s" }}
          >
            PIPO grew out of a simple conviction: that a college should be judged
            by what it does for its students, not by the privilege it admits. The
            project is led by a university president who has spent his career
            close to the question of student persistence.
          </p>
        </div>
      </section>

      {/* ── Profile ──────────────────────────────────────────── */}
      <section className="mx-auto w-full max-w-7xl px-6 py-16 sm:py-20">
        <div className="grid gap-12 lg:grid-cols-[minmax(0,20rem)_1fr] lg:gap-16">
          {/* Portrait */}
          <div className="reveal-fade lg:sticky lg:top-24 lg:self-start">
            <div className="overflow-hidden rounded-lg border border-rule bg-panel">
              <Image
                src={headshot}
                alt="Portrait of Dan Myers"
                placeholder="blur"
                sizes="(max-width: 1024px) 100vw, 20rem"
                className="h-auto w-full object-cover"
                priority
              />
              <div className="border-t border-rule px-4 py-3.5">
                <p className="font-display text-lg font-semibold leading-tight tracking-tight text-ink">
                  Dan Myers
                </p>
                <p className="mt-1 font-mono text-[11px] uppercase tracking-[0.16em] text-ink-soft">
                  15th President, Misericordia University
                </p>
              </div>
            </div>
          </div>

          {/* Bio */}
          <div className="max-w-2xl">
            <div className="space-y-5 text-[1.05rem] leading-relaxed text-ink-soft [&_strong]:font-medium [&_strong]:text-ink">
              <p>
                <strong>Dan Myers</strong> is the 15th President of Misericordia
                University in Pennsylvania. Prior to his appointment at
                Misericordia, he served as the Chief Academic Officer (Provost)
                at American University in Washington, DC and at Marquette
                University in Wisconsin. In both of those positions, he oversaw
                the student persistence operation and has taken a keen interest
                in it as a university president as well.
              </p>
              <p>
                Prior to his provost roles, he spent 17 years at the University
                of Notre Dame, where he was Professor of Sociology and Vice
                President for Faculty Affairs. Dr. Myers was also the director of
                Faculty Development and Research in the Kroc Institute for
                International Peace Studies, and he founded and directed Notre
                Dame&rsquo;s Center for the Study of Social Movements.
              </p>
              <p>
                Dr. Myers earned a bachelor&rsquo;s degree in political science
                and a master&rsquo;s degree in higher education and student
                affairs from Ohio State University before completing a
                master&rsquo;s and doctorate in sociology at the University of
                Wisconsin-Madison. His primary expertise is in the study of
                protest, activism, collective behavior, and social movements.
              </p>
              <p>
                He has published eight books and over 60 articles primarily
                focused on protest and unrest, mathematical models of the
                diffusion of social phenomena, social psychology, game theory,
                and urban politics. He is an award-winning teacher and
                researcher, and was honored with Notre Dame&rsquo;s highest
                teaching award in 2007. His research has been funded by the
                National Science Foundation and the Lilly Foundation. He has
                served on a variety of non-profit boards of arts, health, and
                educational organizations.
              </p>
            </div>

            {/* Credentials strip */}
            <dl className="mt-12 grid grid-cols-2 border-t border-rule sm:grid-cols-4 sm:divide-x sm:divide-rule">
              {MARKS.map((m) => (
                <div key={m.l} className="px-1 py-6 sm:px-5 sm:first:pl-0">
                  <dt className="font-mono text-3xl tabular-nums tracking-tight text-ink">
                    {m.n}
                  </dt>
                  <dd className="mt-1 font-mono text-[11px] uppercase leading-snug tracking-[0.14em] text-ink-soft">
                    {m.l}
                  </dd>
                </div>
              ))}
            </dl>

            <div className="mt-12">
              <Link
                href="/"
                className="link-underline font-mono text-[12px] uppercase tracking-[0.16em] text-ink-soft hover:text-ink"
              >
                &larr; Back to the index
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
