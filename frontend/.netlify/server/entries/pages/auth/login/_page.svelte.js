import { a0 as head, _ as attr } from "../../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/state.svelte.js";
import { p as page } from "../../../../chunks/index4.js";
import { e as escape_html } from "../../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { form } = $$props;
    let isLoading = false;
    let totpRequired = form?.requiresTotp === true;
    let totpToken = form?.totpToken || "";
    let email = form?.email || "";
    let error = form?.error || page.url.searchParams.get("error") || null;
    head("1i2smtp", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Sign In - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="login-container svelte-1i2smtp"><div class="login-card svelte-1i2smtp"><div class="login-header svelte-1i2smtp"><span class="login-icon svelte-1i2smtp">🏘️</span> <h1 class="svelte-1i2smtp">Welcome Back</h1> <p class="svelte-1i2smtp">Sign in to access the Community Resilience platform</p></div> `);
    if (error) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="error-message svelte-1i2smtp">${escape_html(error)}</div>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (totpRequired) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<form class="totp-form svelte-1i2smtp" method="POST" action="?/verifyTotp"><input type="hidden" name="totp_token"${attr("value", totpToken)}/> <input type="hidden" name="email"${attr("value", email)}/> <p class="totp-prompt svelte-1i2smtp">Enter the 6-digit code from your authenticator app.</p> <input type="text" name="code" placeholder="000000" maxlength="6" pattern="[0-9]*" inputmode="numeric" autocomplete="one-time-code" class="totp-input svelte-1i2smtp" required${attr("disabled", isLoading, true)}/> <button type="submit" class="submit-button svelte-1i2smtp"${attr("disabled", isLoading, true)}>${escape_html("Verify")}</button> <a href="/auth/login" class="back-link svelte-1i2smtp">Back to login</a></form>`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<form class="password-form svelte-1i2smtp" method="POST" action="?/login"><input type="email" name="email"${attr("value", email)} placeholder="Email address" autocomplete="email" class="form-input svelte-1i2smtp" required${attr("disabled", isLoading, true)}/> <div class="password-input-wrapper svelte-1i2smtp"><input${attr("type", "password")} name="password" placeholder="Password" autocomplete="current-password" class="form-input password-input svelte-1i2smtp" required${attr("disabled", isLoading, true)}/> <button type="button" class="password-toggle svelte-1i2smtp"${attr("aria-label", "Show password")}${attr("disabled", isLoading, true)}>`);
      {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push(`<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>`);
      }
      $$renderer2.push(`<!--]--></button></div> <div class="form-footer svelte-1i2smtp"><a href="/auth/forgot-password" class="forgot-password-link svelte-1i2smtp">Forgot password?</a></div> <button type="submit" class="submit-button svelte-1i2smtp"${attr("disabled", isLoading, true)}>${escape_html("Sign In")}</button></form> <p class="register-link svelte-1i2smtp">Don't have an account? <a href="/auth/register" class="svelte-1i2smtp">Create one</a></p> `);
      {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="divider svelte-1i2smtp"><span class="svelte-1i2smtp">or continue with</span></div> <div class="login-buttons svelte-1i2smtp"><button class="oauth-button google svelte-1i2smtp"${attr("disabled", isLoading, true)}><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"></path><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"></path><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"></path><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"></path></svg> <span>Google</span></button> <button class="oauth-button github svelte-1i2smtp"${attr("disabled", isLoading, true)}><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"></path></svg> <span>GitHub</span></button> <button class="oauth-button microsoft svelte-1i2smtp"${attr("disabled", isLoading, true)}><svg viewBox="0 0 24 24" width="20" height="20"><path fill="#f25022" d="M1 1h10v10H1z"></path><path fill="#00a4ef" d="M1 13h10v10H1z"></path><path fill="#7fba00" d="M13 1h10v10H13z"></path><path fill="#ffb900" d="M13 13h10v10H13z"></path></svg> <span>Microsoft</span></button></div>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--> `);
    if (!totpRequired) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="login-footer svelte-1i2smtp"><p class="svelte-1i2smtp">By signing in, you agree to our terms of service and privacy policy.</p></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div></div>`);
  });
}
export {
  _page as default
};
