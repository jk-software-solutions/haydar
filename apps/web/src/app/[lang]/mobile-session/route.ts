// The reverse proxy sends /api/* to FastAPI, so the Flutter WebView uses this
// locale-prefixed web route for the cookie hand-off instead of the API prefix.
export { GET } from "../../api/mobile-session/route";
