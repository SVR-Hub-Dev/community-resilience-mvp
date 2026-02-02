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
    let token = page.url.searchParams.get("token") || "";
    head("654myr", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Reset Password - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="reset-password-container svelte-654myr"><div class="reset-password-card svelte-654myr"><div class="header svelte-654myr"><span class="icon svelte-654myr">🔐</span> <h1 class="svelte-654myr">Create New Password</h1> <p class="svelte-654myr">Enter your new password below.</p></div> `);
    if (!token) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="error-message svelte-654myr"><svg viewBox="0 0 20 20" width="20" height="20" class="svelte-654myr"><path fill="currentColor" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"></path></svg> <div><strong class="svelte-654myr">Invalid Reset Link</strong> <p class="svelte-654myr">This password reset link is invalid or has expired.</p></div></div> <a href="/auth/forgot-password" class="link-button svelte-654myr">Request New Reset Link</a>`);
    } else {
      $$renderer2.push("<!--[!-->");
      if (form?.success) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="success-message svelte-654myr"><svg viewBox="0 0 20 20" width="20" height="20" class="svelte-654myr"><path fill="currentColor" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"></path></svg> <div><strong class="svelte-654myr">Password Reset Successful</strong> <p class="svelte-654myr">Your password has been successfully reset. You can now sign in with your new password.</p></div></div> <a href="/auth/login" class="link-button svelte-654myr">Sign In</a>`);
      } else {
        $$renderer2.push("<!--[!-->");
        if (form?.error) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<div class="error-message svelte-654myr">${escape_html(form.error)}</div>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--> <form method="POST" class="svelte-654myr"><input type="hidden" name="token"${attr("value", token)}/> <div class="password-input-wrapper svelte-654myr"><input${attr("type", "password")} name="password" placeholder="New password" autocomplete="new-password" class="form-input password-input svelte-654myr" minlength="8" required${attr("disabled", isLoading, true)}/> <button type="button" class="password-toggle svelte-654myr"${attr("aria-label", "Show password")}${attr("disabled", isLoading, true)}>`);
        {
          $$renderer2.push("<!--[!-->");
          $$renderer2.push(`<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>`);
        }
        $$renderer2.push(`<!--]--></button></div> <div class="password-input-wrapper svelte-654myr"><input${attr("type", "password")} name="confirmPassword" placeholder="Confirm new password" autocomplete="new-password" class="form-input password-input svelte-654myr" minlength="8" required${attr("disabled", isLoading, true)}/> <button type="button" class="password-toggle svelte-654myr"${attr("aria-label", "Show password")}${attr("disabled", isLoading, true)}>`);
        {
          $$renderer2.push("<!--[!-->");
          $$renderer2.push(`<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>`);
        }
        $$renderer2.push(`<!--]--></button></div> <div class="password-requirements svelte-654myr"><p class="svelte-654myr">Password must be at least 8 characters long.</p></div> <button type="submit" class="submit-button svelte-654myr"${attr("disabled", isLoading, true)}>${escape_html("Reset Password")}</button></form> <a href="/auth/login" class="back-link svelte-654myr">Back to login</a>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></div></div>`);
  });
}
export {
  _page as default
};
