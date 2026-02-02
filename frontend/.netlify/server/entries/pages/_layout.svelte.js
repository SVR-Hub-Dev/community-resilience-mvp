import { Z as store_get, _ as attr, $ as unsubscribe_stores } from "../../chunks/index2.js";
import { g as getAuthHelpers, p as page } from "../../chunks/auth.svelte.js";
import { e as escape_html } from "../../chunks/context.js";
function _layout($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    var $$store_subs;
    let { children } = $$props;
    let auth = getAuthHelpers(store_get($$store_subs ??= {}, "$page", page).data.user);
    $$renderer2.push(`<div class="layout svelte-12qhfyh"><header class="header svelte-12qhfyh"><div class="container header-inner svelte-12qhfyh"><a href="/" class="logo svelte-12qhfyh"><img src="/SVRLogo.png" alt="Logo" class="logo-icon svelte-12qhfyh" style="width: 1.5em; height: 1.5em; vertical-align: middle;"/> <span class="logo-text">Resilience Hub</span></a> <h1 class="site-heading" style="margin: 0 2rem; font-size: 1.5rem; font-weight: 700; color: var(--primary, #2563eb); text-align: center;">Batlow Community Knowledge Base</h1> <nav class="nav svelte-12qhfyh"><a href="/" class="nav-link svelte-12qhfyh">Query</a> <a href="/knowledge" class="nav-link svelte-12qhfyh">Knowledge</a> <a href="/knowledge-graph" class="nav-link svelte-12qhfyh">Graph</a> <a href="/documents" class="nav-link svelte-12qhfyh">Documents</a> <a href="/events" class="nav-link svelte-12qhfyh">Events</a> <a href="/assets" class="nav-link svelte-12qhfyh">Assets</a> `);
    if (auth.isAuthenticated && auth.user) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="user-menu-container svelte-12qhfyh"><button class="user-button svelte-12qhfyh">`);
      if (auth.user.avatar_url) {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<img${attr("src", auth.user.avatar_url)} alt="" class="user-avatar svelte-12qhfyh"/>`);
      } else {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push(`<span class="user-avatar-placeholder svelte-12qhfyh">${escape_html((auth.user.name || auth.user.email).charAt(0).toUpperCase())}</span>`);
      }
      $$renderer2.push(`<!--]--> <span class="user-name svelte-12qhfyh">${escape_html(auth.user.name || auth.user.email)}</span> <svg class="dropdown-icon svelte-12qhfyh" viewBox="0 0 20 20" width="16" height="16"><path fill="currentColor" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"></path></svg></button> `);
      {
        $$renderer2.push("<!--[!-->");
      }
      $$renderer2.push(`<!--]--></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`<a href="/auth/login" class="sign-in-button svelte-12qhfyh">Sign In</a>`);
    }
    $$renderer2.push(`<!--]--></nav></div></header> <main class="main svelte-12qhfyh">`);
    children($$renderer2);
    $$renderer2.push(`<!----></main> <footer class="footer svelte-12qhfyh"><div class="container"><p>Community Resilience Reasoning Model MVP</p></div></footer></div>`);
    if ($$store_subs) unsubscribe_stores($$store_subs);
  });
}
export {
  _layout as default
};
