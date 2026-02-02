import { fail, redirect } from "@sveltejs/kit";
import { b as backend } from "../../../../chunks/backend.js";
import { b as private_env } from "../../../../chunks/shared-server.js";
import { d as dev } from "../../../../chunks/index3.js";
const SESSION_COOKIE_NAME = "session_id";
const API_URL = private_env.API_URL || "http://localhost:8000";
const load = async ({ locals }) => {
  if (locals.user) {
    throw redirect(302, "/");
  }
  return {};
};
const actions = {
  default: async ({ request, cookies }) => {
    const formData = await request.formData();
    const name = formData.get("name")?.toString() || "";
    const email = formData.get("email")?.toString() || "";
    const password = formData.get("password")?.toString() || "";
    const confirmPassword = formData.get("confirmPassword")?.toString() || "";
    if (!name || !email || !password) {
      return fail(400, { error: "All fields are required", email, name });
    }
    if (password.length < 8) {
      return fail(400, { error: "Password must be at least 8 characters", email, name });
    }
    if (password !== confirmPassword) {
      return fail(400, { error: "Passwords do not match", email, name });
    }
    try {
      const response = await fetch(`${API_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name })
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Registration failed" }));
        return fail(response.status, {
          error: errorData.detail || "Registration failed",
          email,
          name
        });
      }
      const result = await response.json();
      const session = await backend.createSession(result.user.id);
      cookies.set(SESSION_COOKIE_NAME, session.session_id, {
        path: "/",
        httpOnly: true,
        secure: !dev,
        sameSite: "lax",
        maxAge: 60 * 60 * 24 * 7
        // 7 days
      });
      throw redirect(302, "/");
    } catch (err) {
      if (err instanceof Response || err?.status === 302) {
        throw err;
      }
      console.error("Registration error:", err);
      return fail(500, {
        error: err instanceof Error ? err.message : "Registration failed",
        email,
        name
      });
    }
  }
};
export {
  actions,
  load
};
