import { collegeNavigatorUrl } from "@/lib/links";

/**
 * An institution name rendered as a link to its NCES College Navigator page
 * (opens in a new tab). Used wherever a school name is shown as plain text
 * (data tables, tooltips), matching the legacy tool where every college name
 * deep-linked to College Navigator.
 */
export default function CollegeNavLink({
  unitid,
  name,
  className = "",
}: {
  unitid: number;
  name: string;
  className?: string;
}) {
  return (
    <a
      href={collegeNavigatorUrl(unitid)}
      target="_blank"
      rel="noopener noreferrer"
      title={`${name} — open on College Navigator ↗`}
      className={`underline decoration-rule decoration-dotted underline-offset-2 transition-colors hover:text-teal hover:decoration-teal ${className}`}
    >
      {name}
    </a>
  );
}
