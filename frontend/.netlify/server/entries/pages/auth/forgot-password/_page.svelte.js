import { a0 as head, _ as attr } from "../../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/state.svelte.js";
import { e as escape_html } from "../../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let { form } = $$props;
    let isLoading = false;
    head("c68gvn", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Forgot Password - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="forgot-password-container svelte-c68gvn"><div class="forgot-password-card svelte-c68gvn"><div class="header svelte-c68gvn"><span class="icon svelte-c68gvn">🔑</span> <h1 class="svelte-c68gvn">Reset Password</h1> <p class="svelte-c68gvn">Enter your email address and we'll send you a link to reset your password.</p></div> `);
    if (form?.success) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="success-message svelte-c68gvn"><svg viewBox="0 0 20 20" width="20" height="20" class="svelte-c68gvn"><path fill="currentColor" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"></path></svg> <div><strong class="svelte-c68gvn">Check your email</strong> <p class="svelte-c68gvn">If an account exists with that email, we've sent password reset instructions.
						Please check your inbox and spam folder.</p></div></div> <a href="/auth/login" class="back-link svelte-c68gvn">Back to login</a>`);
    } else {
      $$renderer2.push("<!--[!-->");
      if (form?.error) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="error-message svelte-c68gvn">${escape_html(form.error)}</div>`);
      } else {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--> <form method="POST" class="svelte-c68gvn"><input type="email" name="email" placeholder="Email address" autocomplete="email" class="form-input svelte-c68gvn" required${attr("disabled", isLoading, true)}/> <button type="submit" class="submit-button svelte-c68gvn"${attr("disabled", isLoading, true)}>${escape_html("Send Reset Link")}</button></form> <a href="/auth/login" class="back-link svelte-c68gvn">Back to login</a>`);
    }
    $$renderer2.push(`<!--]--></div></div>`);
  });
}
export {
  _page as default
};
