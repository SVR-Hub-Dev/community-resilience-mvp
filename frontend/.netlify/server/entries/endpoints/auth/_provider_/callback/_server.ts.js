import { error, redirect } from "@sveltejs/kit";
import { d as dev } from "../../../../../chunks/index3.js";
import { i as isValidProvider, e as exchangeCodeForToken, f as fetchUserInfo } from "../../../../../chunks/oauth.js";
import { b as backend } from "../../../../../chunks/backend.js";
const STATE_COOKIE_NAME = "oauth_state";
const SESSION_COOKIE_NAME = "session_id";
const SESSION_TTL_SECONDS = 7 * 24 * 60 * 60;
const GET = async ({ params, url, cookies }) => {
  const { provider } = params;
  if (!isValidProvider(provider)) {
    throw error(400, `Invalid OAuth provider: ${provider}`);
  }
  const typedProvider = provider;
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const errorParam = url.searchParams.get("error");
  const errorDescription = url.searchParams.get("error_description");
  if (errorParam) {
    console.error(`OAuth error from ${provider}: ${errorParam} - ${errorDescription}`);
    throw redirect(302, `/auth/login?error=${encodeURIComponent(errorDescription || errorParam)}`);
  }
  if (!code || !state) {
    throw redirect(302, "/auth/login?error=Missing authorization code or state");
  }
  const storedState = cookies.get(STATE_COOKIE_NAME);
  cookies.delete(STATE_COOKIE_NAME, { path: "/" });
  if (!storedState || storedState !== state) {
    console.error("OAuth state mismatch - possible CSRF attack");
    throw redirect(302, "/auth/login?error=Invalid state parameter");
  }
  try {
    const redirectUri = `${url.origin}/auth/${provider}/callback`;
    const tokenResponse = await exchangeCodeForToken(typedProvider, code, redirectUri);
    const userInfo = await fetchUserInfo(typedProvider, tokenResponse.access_token);
    const oauthResult = await backend.oauthFindOrCreate({
      provider: userInfo.provider,
      provider_id: userInfo.provider_id,
      email: userInfo.email,
      name: userInfo.name,
      avatar_url: userInfo.avatar_url
    });
    const { session_id } = await backend.createSession(oauthResult.user_id, SESSION_TTL_SECONDS);
    cookies.set(SESSION_COOKIE_NAME, session_id, {
      path: "/",
      httpOnly: true,
      secure: !dev,
      sameSite: "lax",
      maxAge: SESSION_TTL_SECONDS
    });
    throw redirect(302, "/");
  } catch (err) {
    if (err instanceof Response) {
      throw err;
    }
    console.error(`OAuth callback error for ${provider}:`, err);
    const errorMessage = err instanceof Error ? err.message : "Authentication failed. Please try again.";
    throw redirect(302, `/auth/login?error=${encodeURIComponent(errorMessage)}`);
  }
};
export {
  GET
};
