import { a1 as attr_class, a2 as stringify, a0 as head, a3 as ensure_array_like } from "../../../chunks/index2.js";
import { e as escape_html } from "../../../chunks/context.js";
function DocumentStatusBadge($$renderer, $$props) {
  let { processingStatus, processingMode, needsFullProcessing } = $$props;
  const statusConfig = {
    completed: { label: "Fully Processed", class: "badge-success" },
    needs_local: { label: "Pending Sync", class: "badge-warning" },
    pending: { label: "Pending", class: "badge-secondary" },
    processing: { label: "Processing...", class: "badge-primary" },
    failed: { label: "Failed", class: "badge-danger" }
  };
  let status = statusConfig[processingStatus] ?? { label: processingStatus, class: "badge-secondary" };
  let modeLabel = processingMode === "cloud_basic" ? "Basic" : processingMode === "local_full" ? "Full" : processingMode;
  $$renderer.push(`<span class="badge-group svelte-1xfmgl2"><span${attr_class(`badge ${stringify(status.class)}`, "svelte-1xfmgl2")}>${escape_html(status.label)}</span> `);
  if (needsFullProcessing) {
    $$renderer.push("<!--[-->");
    $$renderer.push(`<span class="badge badge-info svelte-1xfmgl2" title="Full processing will occur when synced to a local instance">Awaiting Full Processing</span>`);
  } else {
    $$renderer.push("<!--[!-->");
    $$renderer.push(`<span class="badge badge-mode svelte-1xfmgl2">${escape_html(modeLabel)}</span>`);
  }
  $$renderer.push(`<!--]--></span>`);
}
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let uploadedDocs = [];
    head("220hbx", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Documents - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="container"><div class="page-header svelte-220hbx"><div class="header-row svelte-220hbx"><h1 class="svelte-220hbx">Documents</h1> <button class="btn btn-primary">${escape_html("Upload Document")}</button></div> <p class="svelte-220hbx">Upload and manage community knowledge documents.</p></div> `);
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
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    if (uploadedDocs.length > 0) {
      $$renderer2.push("<!--[-->");
      $$renderer2.push(`<h2 class="section-title svelte-220hbx">Uploaded Documents</h2> <div class="doc-list svelte-220hbx"><!--[-->`);
      const each_array = ensure_array_like(uploadedDocs);
      for (let $$index = 0, $$length = each_array.length; $$index < $$length; $$index++) {
        let doc = each_array[$$index];
        $$renderer2.push(`<div class="card doc-card svelte-220hbx"><div class="doc-header svelte-220hbx"><h3 class="svelte-220hbx">${escape_html(doc.title)}</h3> `);
        DocumentStatusBadge($$renderer2, {
          processingStatus: doc.processing_status,
          processingMode: doc.processing_mode,
          needsFullProcessing: doc.needs_full_processing
        });
        $$renderer2.push(`<!----></div> <p class="doc-message svelte-220hbx">${escape_html(doc.message)}</p> `);
        if (doc.needs_full_processing) {
          $$renderer2.push("<!--[-->");
          $$renderer2.push(`<p class="doc-sync-note svelte-220hbx">Full processing (OCR, structured extraction) will occur when this document is
							synced to a local instance.</p>`);
        } else {
          $$renderer2.push("<!--[!-->");
        }
        $$renderer2.push(`<!--]--> <div class="doc-actions svelte-220hbx"><button class="btn btn-secondary btn-sm svelte-220hbx">Refresh Status</button></div></div>`);
      }
      $$renderer2.push(`<!--]--></div>`);
    } else {
      $$renderer2.push("<!--[!-->");
      {
        $$renderer2.push("<!--[-->");
        $$renderer2.push(`<div class="card empty-state svelte-220hbx"><p>No documents uploaded yet. Click "Upload Document" to get started.</p></div>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></div>`);
  });
}
export {
  _page as default
};
