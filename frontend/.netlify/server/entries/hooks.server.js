import { b as backend } from "../chunks/backend.js";
const SESSION_COOKIE_NAME = "session_id";
const handle = async ({ event, resolve }) => {
  const sessionId = event.cookies.get(SESSION_COOKIE_NAME);
  if (sessionId) {
    try {
      const user = await backend.validateSession(sessionId);
      event.locals.user = {
        id: user.id,
        email: user.email || "",
        role: user.role || "viewer"
      };
    } catch (err) {
      event.cookies.delete(SESSION_COOKIE_NAME, { path: "/" });
      event.locals.user = null;
    }
  } else {
    event.locals.user = null;
  }
  return resolve(event);
};
export {
  handle
};
