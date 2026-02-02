import { a0 as head, _ as attr } from "../../chunks/index2.js";
import { e as escape_html } from "../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let situationText = "";
    let loading = false;
    head("1uha8ag", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Community Resilience - Query</title>`);
      });
    });
    $$renderer2.push(`<div class="container"><div class="page-header svelte-1uha8ag"><h1 class="svelte-1uha8ag">Disaster Response Assistant</h1> <p class="svelte-1uha8ag">Describe your current situation to receive prioritized action recommendations based on local community knowledge.</p></div> <div class="query-section card svelte-1uha8ag"><form><label class="label" for="situation">Current Situation</label> <textarea id="situation" class="textarea" placeholder="Describe what's happening. Example: Heavy rain, Riverside Street flooding, power out in the area..."${attr("disabled", loading, true)}>`);
    const $$body = escape_html(situationText);
    if ($$body) {
      $$renderer2.push(`${$$body}`);
    }
    $$renderer2.push(`</textarea> <div class="submit-row svelte-1uha8ag"><button type="submit" class="btn btn-primary"${attr("disabled", !situationText.trim(), true)}>`);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`Get Recommendations`);
    }
    $$renderer2.push(`<!--]--></button></div></form></div> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
