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
    head("1ntfpny", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>${escape_html("Entity")} - Knowledge Graph</title>`);
      });
    });
    $$renderer2.push(`<div class="container"><nav class="breadcrumb svelte-1ntfpny"><a href="/knowledge-graph" class="svelte-1ntfpny">Knowledge Graph</a> <span class="sep svelte-1ntfpny">/</span> <span>${escape_html("Loading...")}</span></nav> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<div class="loading"><div class="spinner"></div></div>`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
