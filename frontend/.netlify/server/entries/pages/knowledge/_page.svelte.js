import { a0 as head } from "../../../chunks/index2.js";
import { e as escape_html } from "../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    head("u7nvcr", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Knowledge Base - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="container"><div class="page-header svelte-u7nvcr"><div class="header-row svelte-u7nvcr"><h1 class="svelte-u7nvcr">Knowledge Base</h1> <button class="btn btn-primary">${escape_html("Add Entry")}</button></div> <p class="svelte-u7nvcr">Community knowledge entries used for disaster response recommendations.</p></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
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
