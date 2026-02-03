import * as server from '../entries/pages/auth/register/_page.server.ts.js';

export const index = 8;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/auth/register/_page.svelte.js')).default;
export { server };
export const server_id = "src/routes/auth/register/+page.server.ts";
export const imports = ["_app/immutable/nodes/8.DC1KITdu.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/IYHzjH-u.js","_app/immutable/chunks/y2AUGcWI.js","_app/immutable/chunks/D5TtrX9z.js","_app/immutable/chunks/DUqvfk82.js","_app/immutable/chunks/BzuisjXd.js","_app/immutable/chunks/DlUCU2Pc.js","_app/immutable/chunks/C_FbWKzR.js","_app/immutable/chunks/NLJqMFdk.js","_app/immutable/chunks/Mv_31n4n.js","_app/immutable/chunks/D8dhbHQO.js","_app/immutable/chunks/CGMLLeuR.js"];
export const stylesheets = ["_app/immutable/assets/8.BhY1Z-ij.css"];
export const fonts = [];
