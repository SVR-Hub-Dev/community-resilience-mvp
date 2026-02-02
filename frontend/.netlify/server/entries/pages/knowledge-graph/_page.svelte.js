import { a0 as head, a1 as attr_class, a3 as ensure_array_like, _ as attr } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/state.svelte.js";
import { e as escape_html } from "../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    const ENTITY_TYPES = [
      "HazardType",
      "Community",
      "Agency",
      "Location",
      "Resource",
      "Action"
    ];
    let total = 0;
    let selectedType = "";
    let searchQuery = "";
    head("n1dg1y", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Knowledge Graph - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="container"><div class="page-header svelte-n1dg1y"><div class="header-row svelte-n1dg1y"><h1 class="svelte-n1dg1y">Knowledge Graph</h1></div> <p class="svelte-n1dg1y">Structured entities and relationships extracted from community documents.</p></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <div class="filters-bar svelte-n1dg1y"><div class="type-filters svelte-n1dg1y"><button${attr_class("filter-btn svelte-n1dg1y", void 0, { "active": selectedType === "" })}>All</button> <!--[-->`);
    const each_array_1 = ensure_array_like(ENTITY_TYPES);
    for (let $$index_1 = 0, $$length = each_array_1.length; $$index_1 < $$length; $$index_1++) {
      let type = each_array_1[$$index_1];
      $$renderer2.push(`<button${attr_class("filter-btn svelte-n1dg1y", void 0, { "active": selectedType === type })}>${escape_html(type)}</button>`);
    }
    $$renderer2.push(`<!--]--></div> <div class="search-box svelte-n1dg1y"><input type="text" class="input search-input svelte-n1dg1y" placeholder="Search entities..."${attr("value", searchQuery)}/></div></div> <p class="results-count svelte-n1dg1y">${escape_html(total)} ${escape_html("entities")} found `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></p> `);
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
