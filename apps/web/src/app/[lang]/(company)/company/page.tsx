import { notFound } from "next/navigation";

export default function CompanyPortalFoundation() {
  // The route group exists, but no company portal content is exposed until the
  // real backend authentication and membership policy milestone is complete.
  notFound();
}
