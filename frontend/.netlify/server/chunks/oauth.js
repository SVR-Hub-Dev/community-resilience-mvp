import { b as private_env } from "./shared-server.js";
const OAUTH_CONFIGS = {
  google: () => ({
    clientId: private_env.GOOGLE_CLIENT_ID || "",
    clientSecret: private_env.GOOGLE_CLIENT_SECRET || "",
    authUrl: "https://accounts.google.com/o/oauth2/v2/auth",
    tokenUrl: "https://oauth2.googleapis.com/token",
    userInfoUrl: "https://openidconnect.googleapis.com/v1/userinfo",
    scopes: ["openid", "email", "profile"]
  }),
  github: () => ({
    clientId: private_env.GITHUB_CLIENT_ID || "",
    clientSecret: private_env.GITHUB_CLIENT_SECRET || "",
    authUrl: "https://github.com/login/oauth/authorize",
    tokenUrl: "https://github.com/login/oauth/access_token",
    userInfoUrl: "https://api.github.com/user",
    scopes: ["read:user", "user:email"]
  }),
  microsoft: () => ({
    clientId: private_env.MICROSOFT_CLIENT_ID || "",
    clientSecret: private_env.MICROSOFT_CLIENT_SECRET || "",
    authUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    tokenUrl: "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    userInfoUrl: "https://graph.microsoft.com/v1.0/me",
    scopes: ["openid", "email", "profile", "User.Read"]
  })
};
function isValidProvider(provider) {
  return ["google", "github", "microsoft"].includes(provider);
}
function getOAuthConfig(provider) {
  return OAUTH_CONFIGS[provider]();
}
function generateState() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, "0")).join("");
}
function buildAuthorizationUrl(provider, redirectUri, state) {
  const config = getOAuthConfig(provider);
  if (!config.clientId) {
    throw new Error(`OAuth client ID not configured for ${provider}`);
  }
  const params = new URLSearchParams({
    client_id: config.clientId,
    redirect_uri: redirectUri,
    response_type: "code",
    scope: config.scopes.join(" "),
    state
  });
  if (provider === "google") {
    params.set("access_type", "offline");
    params.set("prompt", "consent");
  }
  return `${config.authUrl}?${params.toString()}`;
}
async function exchangeCodeForToken(provider, code, redirectUri) {
  const config = getOAuthConfig(provider);
  const params = new URLSearchParams({
    client_id: config.clientId,
    client_secret: config.clientSecret,
    code,
    redirect_uri: redirectUri,
    grant_type: "authorization_code"
  });
  const headers = {
    "Content-Type": "application/x-www-form-urlencoded"
  };
  if (provider === "github") {
    headers["Accept"] = "application/json";
  }
  const response = await fetch(config.tokenUrl, {
    method: "POST",
    headers,
    body: params.toString()
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Token exchange failed: ${response.status} - ${errorText}`);
  }
  return response.json();
}
async function fetchUserInfo(provider, accessToken) {
  const config = getOAuthConfig(provider);
  const response = await fetch(config.userInfoUrl, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/json"
    }
  });
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`User info fetch failed: ${response.status} - ${errorText}`);
  }
  const data = await response.json();
  switch (provider) {
    case "google":
      return {
        provider,
        provider_id: data.sub,
        email: data.email,
        name: data.name || data.email.split("@")[0],
        avatar_url: data.picture
      };
    case "github": {
      let email = data.email;
      if (!email) {
        email = await fetchGitHubPrimaryEmail(accessToken);
      }
      return {
        provider,
        provider_id: String(data.id),
        email,
        name: data.name || data.login,
        avatar_url: data.avatar_url
      };
    }
    case "microsoft":
      return {
        provider,
        provider_id: data.id,
        email: data.mail || data.userPrincipalName,
        name: data.displayName || data.userPrincipalName.split("@")[0],
        avatar_url: void 0
        // Microsoft Graph requires separate call for photo
      };
  }
}
async function fetchGitHubPrimaryEmail(accessToken) {
  const response = await fetch("https://api.github.com/user/emails", {
    headers: {
      Authorization: `Bearer ${accessToken}`,
      Accept: "application/json"
    }
  });
  if (!response.ok) {
    throw new Error("Failed to fetch GitHub emails");
  }
  const emails = await response.json();
  const primary = emails.find((e) => e.primary);
  if (!primary) {
    throw new Error("No primary email found on GitHub account");
  }
  return primary.email;
}
export {
  buildAuthorizationUrl as b,
  exchangeCodeForToken as e,
  fetchUserInfo as f,
  generateState as g,
  isValidProvider as i
};
