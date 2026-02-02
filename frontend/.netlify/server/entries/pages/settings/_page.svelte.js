import { a0 as head, _ as attr } from "../../../chunks/index2.js";
import "@sveltejs/kit/internal";
import "../../../chunks/exports.js";
import "../../../chunks/utils.js";
import "@sveltejs/kit/internal/server";
import "../../../chunks/state.svelte.js";
import { e as escape_html } from "../../../chunks/context.js";
function _page($$renderer, $$props) {
  $$renderer.component(($$renderer2) => {
    let isLoading = false;
    let newPassword = "";
    let confirmPassword = "";
    let themeMode = "system";
    head("1i19ct2", $$renderer2, ($$renderer3) => {
      $$renderer3.title(($$renderer4) => {
        $$renderer4.push(`<title>Settings - Community Resilience</title>`);
      });
    });
    $$renderer2.push(`<div class="settings-container svelte-1i19ct2"><h1 class="svelte-1i19ct2">Settings</h1> <section class="settings-section svelte-1i19ct2"><h2 class="svelte-1i19ct2">Theme</h2> <p class="section-description svelte-1i19ct2">Choose your preferred color mode.</p> <div class="theme-switch svelte-1i19ct2"><label class="svelte-1i19ct2"><input type="radio" name="theme" value="light"${attr("checked", themeMode === "light", true)}/> Light</label> <label class="svelte-1i19ct2"><input type="radio" name="theme" value="dark"${attr("checked", themeMode === "dark", true)}/> Dark</label> <label class="svelte-1i19ct2"><input type="radio" name="theme" value="system"${attr("checked", themeMode === "system", true)}/> System</label></div></section> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> `);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <section class="settings-section svelte-1i19ct2"><h2 class="svelte-1i19ct2">Password</h2> <p class="section-description svelte-1i19ct2">`);
    {
      $$renderer2.push("<!--[!-->");
      $$renderer2.push(`Set a password to enable offline sign-in with your email and password.`);
    }
    $$renderer2.push(`<!--]--></p> <form class="password-form svelte-1i19ct2">`);
    {
      $$renderer2.push("<!--[!-->");
    }
    $$renderer2.push(`<!--]--> <label for="new-password" class="svelte-1i19ct2">${escape_html("Password")}</label> <input id="new-password" type="password"${attr("value", newPassword)} required minlength="8"${attr("disabled", isLoading, true)} autocomplete="new-password" class="svelte-1i19ct2"/> <label for="confirm-password" class="svelte-1i19ct2">Confirm password</label> <input id="confirm-password" type="password"${attr("value", confirmPassword)} required minlength="8"${attr("disabled", isLoading, true)} autocomplete="new-password" class="svelte-1i19ct2"/> <button type="submit" class="btn btn-primary svelte-1i19ct2"${attr("disabled", newPassword.length < 8 || newPassword !== confirmPassword, true)}>${escape_html("Set Password")}</button></form></section> <section class="settings-section svelte-1i19ct2"><h2 class="svelte-1i19ct2">Two-Factor Authentication (TOTP)</h2> <p class="section-description svelte-1i19ct2">Add an extra layer of security by requiring a code from your authenticator app when you sign in.</p> `);
    {
      $$renderer2.push("<!--[!-->");
      {
        $$renderer2.push("<!--[!-->");
        $$renderer2.push(`<div class="totp-status disabled svelte-1i19ct2"><span class="status-badge off svelte-1i19ct2">Not enabled</span> <p class="svelte-1i19ct2">Protect your account with a time-based one-time password.</p> <button class="btn btn-primary svelte-1i19ct2"${attr("disabled", isLoading, true)}>${escape_html("Set Up TOTP")}</button></div>`);
      }
      $$renderer2.push(`<!--]-->`);
    }
    $$renderer2.push(`<!--]--></section></div>`);
  });
}
export {
  _page as default
};
