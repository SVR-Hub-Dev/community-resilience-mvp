import { a0 as head } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "clsx";
import "@sveltejs/kit/internal/server";
import "../../../chunks/state.svelte.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    head("l2iqfo", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>API Keys - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="container"><div class="page-header svelte-l2iqfo"><h1 class="svelte-l2iqfo">API Keys</h1> <p class="svelte-l2iqfo">Manage your API keys for programmatic access to the Community Resilience API.</p></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="card svelte-l2iqfo"><div class="card-header svelte-l2iqfo"><h2 class="svelte-l2iqfo">Your API Keys</h2> <button class="btn btn-primary svelte-l2iqfo">Create New Key</button></div> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-l2iqfo">Loading...</div>`);
    }
    $$renderer2.push(`<!--]--></div></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}
export {
  _page as default
};
