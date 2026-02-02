import { error, redirect } from "@sveltejs/kit";
import { d as dev } from "../../../../chunks/index3.js";
import { i as isValidProvider, g as generateState, b as buildAuthorizationUrl } from "../../../../chunks/oauth.js";
const STATE_COOKIE_NAME = "oauth_state";
const STATE_COOKIE_MAX_AGE = 60 * 10;
const GET = async ({ params, url, cookies }) => {
  const { provider } = params;
  if (!isValidProvider(provider)) {
    throw error(400, `Invalid OAuth provider: ${provider}`);
  }
  const state = generateState();
  cookies.set(STATE_COOKIE_NAME, state, {
    path: "/",
    httpOnly: true,
    secure: !dev,
    sameSite: "lax",
    maxAge: STATE_COOKIE_MAX_AGE
  });
  const redirectUri = `${url.origin}/auth/${provider}/callback`;
  const authUrl = buildAuthorizationUrl(provider, redirectUri, state);
  redirect(302, authUrl);
};
export {
  GET
};
