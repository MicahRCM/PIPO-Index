/** Registry of the tools, shared by the nav and the landing page. */
export interface ToolDef {
  slug: string;
  /** Short code shown in the legacy app (VAI, VAM, …). */
  code: string;
  name: string;
  description: string;
  href: string;
  status: "live" | "coming-soon";
}

export const TOOLS: ToolDef[] = [
  // NOTE: a raw "Retention Trends" tool was deliberately removed. Ranking or
  // comparing schools on raw retention/graduation rates measures the privilege
  // of the incoming class, not what the school does — which is the opposite of
  // this project's argument. Raw rates appear only alongside value-added
  // figures (e.g. in the VAI table), never as a standalone comparison.
  {
    slug: "vai",
    code: "VAI",
    name: "Value-Added Index",
    description: "Sortable ranking of value-added retention and graduation performance.",
    href: "/tools/vai",
    status: "live",
  },
  {
    slug: "vam",
    code: "VAM",
    name: "Value-Added Matrix",
    description: "Scatter of value-added retention vs. graduation across all schools.",
    href: "/tools/vam",
    status: "live",
  },
  {
    slug: "cas",
    code: "CAS",
    name: "Cost After Scholarship",
    description: "Net cost of schools after need- and merit-based scholarships.",
    href: "/tools/cas",
    status: "live",
  },
  {
    slug: "vac",
    code: "VAC",
    name: "Value-Added & Cost",
    description: "Value-added performance vs. cost, broken out by income band.",
    href: "/tools/vac",
    status: "live",
  },
  {
    slug: "map",
    code: "MAP",
    name: "The Atlas Map",
    description:
      "Every institution on a US map, colored and sized by any indicator.",
    href: "/tools/map",
    status: "live",
  },
];

export const LIVE_TOOLS = TOOLS.filter((t) => t.status === "live");
