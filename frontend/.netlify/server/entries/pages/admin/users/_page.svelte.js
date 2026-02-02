import { a0 as head } from "../../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../../chunks/exports.js";
import "../../../../chunks/utils.js";
import { e as escape_html } from "../../../../chunks/context.js";
import "clsx";
import "@sveltejs/kit/internal/server";
import "../../../../chunks/state.svelte.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let total = 0;
    head("1p497kv", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Manage Users - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="container"><div class="page-header svelte-1p497kv"><h1 class="svelte-1p497kv">Manage Users</h1> <p class="svelte-1p497kv">View and manage user accounts and roles.</p></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="card svelte-1p497kv"><div class="card-header svelte-1p497kv"><h2 class="svelte-1p497kv">Users (${escape_html(total)})</h2></div> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading svelte-1p497kv">Loading...</div>`);
    }
    $$renderer2.push(`<!--]--></div></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]-->`);
  });
}
export {
  _page as default
};
