import * as server from '../entries/pages/_layout.server.ts.js';

export const index = 0;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/_layout.svelte.js')).default;
export { server };
export const server_id = "src/routes/+layout.server.ts";
export const imports = ["_app/immutable/nodes/0.xP-8goU2.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/DlUCU2Pc.js","_app/immutable/chunks/IYHzjH-u.js","_app/immutable/chunks/y2AUGcWI.js","_app/immutable/chunks/NLJqMFdk.js","_app/immutable/chunks/Mv_31n4n.js","_app/immutable/chunks/C_FbWKzR.js","_app/immutable/chunks/D8dhbHQO.js","_app/immutable/chunks/BzuisjXd.js","_app/immutable/chunks/CGMLLeuR.js","_app/immutable/chunks/DJgaem7h.js"];
export const stylesheets = ["_app/immutable/assets/0.4JSPV65N.css"];
export const fonts = [];
