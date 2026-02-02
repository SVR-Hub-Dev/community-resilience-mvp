import { g as getContext } from "./context.js";
import "clsx";
import "@sveltejs/kit/internal";
import "./exports.js";
import "./utils.js";
import "@sveltejs/kit/internal/server";
import "./state.svelte.js";
const getStores = () => {
  const stores$1 = getContext("__svelte__");
  return {
    /** @type {typeof page} */
    page: {
      subscribe: stores$1.page.subscribe
    },
    /** @type {typeof navigating} */
    navigating: {
      subscribe: stores$1.navigating.subscribe
    },
    /** @type {typeof updated} */
    updated: stores$1.updated
  };
};
const page = {
  subscribe(fn) {
    const store = getStores().page;
    return store.subscribe(fn);
  }
};
function hasRole(user, roles) {
  return user ? roles.includes(user.role) : false;
}
function isAdmin(user) {
  return hasRole(user, ["admin"]);
}
function canEdit(user) {
  return hasRole(user, ["admin", "editor"]);
}
function getAuthHelpers(user) {
  return {
    user,
    isAuthenticated: !!user,
    isAdmin: isAdmin(user),
    canEdit: canEdit(user)
  };
}
export {
  getAuthHelpers as g,
  page as p
};
