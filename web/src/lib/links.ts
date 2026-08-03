/**
 * External deep-links shared across tools.
 *
 * College Navigator (NCES) keys its institution pages on the IPEDS UNITID,
 * which is exactly the `unitid` we carry on every row — so the school's page is
 * a direct `?id=<unitid>` link, matching the legacy tool's behavior.
 */
export function collegeNavigatorUrl(unitid: number): string {
  return `https://nces.ed.gov/collegenavigator/?id=${unitid}`;
}
