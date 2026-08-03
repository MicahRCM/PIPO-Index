import "server-only";
import type { Institution, MetricValue, RetentionSeries } from "./types";
import rawInstitutions from "../../data/institutions.json";
import rawRetention from "../../data/retention_history.json";

/**
 * Server-side data layer.
 *
 * The ONLY module that knows the raw on-disk JSON format. It normalizes the
 * built merged dataset into the typed `Institution` / `RetentionSeries` the
 * rest of the app consumes. `institutions.json` is produced by
 * data_pipeline/build_app_dataset.py, which JOINS (on unitid) the legacy
 * computed value-added fields with the latest-available canonical variables
 * from the merged data. API routes and components read through this seam, so
 * the data swap stays contained here.
 *
 * Data is imported (not fs-read) so it is bundled into the serverless function
 * and needs no file-tracing config to deploy on Vercel. Normalization runs once
 * at module load and is cached in module scope.
 */

/**
 * Raw shape of a record in institutions.json. `metrics` already carries the
 * legacy value-added fields (vaRetention, vaGraduation, vaDistance, usNewsRank,
 * retentionRate, graduationRate) keyed by their stable variable ids, plus every
 * canonical merged variable keyed by its master-CSV column name. The build
 * script keeps the legacy pubpriv/national encodings on the record so the
 * publicPrivate / nationalUniversity metric ids are derived here, in the seam.
 */
interface RawInstitution {
  unitid: number;
  name: string;
  state: string | null;
  region: string | null;
  /** City / point coordinates from the IPEDS directory (for the Atlas map). */
  city?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  /** 1 = public, 2 = private (legacy IPEDS-style encoding). */
  pubpriv: number | null;
  /** 1 = National University, 0/undefined otherwise. */
  national: number | null;
  metrics: Record<string, MetricValue>;
  /** Provenance: source year per canonical variable (not surfaced on Institution). */
  metricYears?: Record<string, number>;
}

/** Raw shape of retention_history.json. */
interface RawRetention {
  years: number[];
  universities: Record<string, { name: string; rates: (number | null)[] }>;
}

function normalizeInstitution(r: RawInstitution): Institution {
  return {
    unitid: r.unitid,
    name: r.name,
    state: r.state ?? null,
    region: r.region ?? null,
    city: r.city ?? null,
    latitude: r.latitude ?? null,
    longitude: r.longitude ?? null,
    metrics: {
      ...r.metrics,
      nationalUniversity: r.national === 1,
      // pubpriv: 1 = public, 2 = private in the legacy data.
      publicPrivate: r.pubpriv === 1 ? "Public" : r.pubpriv === 2 ? "Private" : null,
      // Average net price = the IPEDS-reported, enrollment-WEIGHTED average
      // across income bands (what College Navigator shows). It is NOT the mean
      // of the 5 bands and can't be reconstructed from them, so we scrape it
      // from Navigator into `avg_net_price_nav` (see
      // data_pipeline/scrape_navigator_avg_netprice.py). Fall back to the old
      // Scorecard public/private column only when the scrape is missing a school.
      avg_net_price:
        r.metrics.avg_net_price_nav ??
        r.metrics.avg_net_price_public ??
        r.metrics.avg_net_price_private ??
        null,
    },
  };
}

const INSTITUTIONS: Institution[] = (rawInstitutions as RawInstitution[]).map(
  normalizeInstitution,
);

const RETENTION: RetentionSeries = (() => {
  const raw = rawRetention as RawRetention;
  const institutions = Object.entries(raw.universities)
    .map(([unitid, info]) => ({
      unitid: Number(unitid),
      name: info.name || "(Unnamed)",
      rates: info.rates,
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
  return { years: raw.years, institutions };
})();

/** Load + normalize all institutions. */
export async function getInstitutions(): Promise<Institution[]> {
  return INSTITUTIONS;
}

/** Load + normalize the retention time series, sorted by name. */
export async function getRetentionSeries(): Promise<RetentionSeries> {
  return RETENTION;
}
