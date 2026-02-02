import { redirect } from "@sveltejs/kit";
import { b as backend } from "../../../chunks/backend.js";
const SESSION_COOKIE_NAME = "session_id";
const GET = async ({ cookies }) => {
  const sessionId = cookies.get(SESSION_COOKIE_NAME);
  if (sessionId) {
    try {
      await backend.deleteSession(sessionId);
    } catch (err) {
      console.error("Failed to delete session from backend:", err);
    }
  }
  cookies.delete(SESSION_COOKIE_NAME, { path: "/" });
  throw redirect(302, "/auth/login");
};
const POST = async ({ cookies }) => {
  const sessionId = cookies.get(SESSION_COOKIE_NAME);
  if (sessionId) {
    try {
      await backend.deleteSession(sessionId);
    } catch (err) {
      console.error("Failed to delete session from backend:", err);
    }
  }
  cookies.delete(SESSION_COOKIE_NAME, { path: "/" });
  throw redirect(302, "/auth/login");
};
export {
  GET,
  POST
};
