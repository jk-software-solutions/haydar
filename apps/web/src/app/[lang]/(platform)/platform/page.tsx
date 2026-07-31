import { notFound } from "next/navigation";

export default function PlatformPortalFoundation() {
  // SUPER_ADMIN session validation is intentionally not mocked during the
  // foundation. The real API-backed guard will replace this closed route.
  notFound();
}
