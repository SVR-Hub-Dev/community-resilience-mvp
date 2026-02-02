import { Z as store_get, a0 as head, _ as attr, $ as unsubscribe_stores } from "../../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/state.svelte.js";
import { g as getAuthHelpers, p as page } from "../../../../chunks/auth.svelte.js";
import { e as escape_html } from "../../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    getAuthHelpers(store_get($$store_subs ??= {}, "$page", page).data.user);
    let isLoading = false;
    let formError = store_get($$store_subs ??= {}, "$page", page).form?.error;
    let formEmail = store_get($$store_subs ??= {}, "$page", page).form?.email || "";
    let formName = store_get($$store_subs ??= {}, "$page", page).form?.name || "";
    head("8bdjn9", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Create Account - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="register-container svelte-8bdjn9"><div class="register-card svelte-8bdjn9"><div class="register-header svelte-8bdjn9"><span class="register-icon svelte-8bdjn9">🏘️</span> <h1 class="svelte-8bdjn9">Create Account</h1> <p class="svelte-8bdjn9">Join the Community Resilience platform</p></div> `);
    if (formError) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="error-message svelte-8bdjn9">${escape_html(formError)}</div>`);
    } else {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <form class="register-form svelte-8bdjn9" method="POST"><input type="text" name="name"${attr("value", formName)} placeholder="Full name" autocomplete="name" class="form-input svelte-8bdjn9" required${attr("disabled", isLoading, true)}/> <input type="email" name="email"${attr("value", formEmail)} placeholder="Email address" autocomplete="email" class="form-input svelte-8bdjn9" required${attr("disabled", isLoading, true)}/> <input type="password" name="password" placeholder="Password (min. 8 characters)" autocomplete="new-password" minlength="8" class="form-input svelte-8bdjn9" required${attr("disabled", isLoading, true)}/> <input type="password" name="confirmPassword" placeholder="Confirm password" autocomplete="new-password" minlength="8" class="form-input svelte-8bdjn9" required${attr("disabled", isLoading, true)}/> <button type="submit" class="submit-button svelte-8bdjn9"${attr("disabled", isLoading, true)}>${escape_html("Create Account")}</button></form> <p class="login-link svelte-8bdjn9">Already have an account? <a href="/auth/login" class="svelte-8bdjn9">Sign in</a></p></div></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _page as default
};
