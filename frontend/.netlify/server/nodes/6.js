import * as server from '../entries/pages/auth/forgot-password/_page.server.ts.js';

export const index = 6;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/auth/forgot-password/_page.svelte.js')).default;
export { server };
export const server_id = "src/routes/auth/forgot-password/+page.server.ts";
export const imports = ["_app/immutable/nodes/6.BJ9t9UR3.js","_app/immutable/chunks/CWj6FrbW.js","_app/immutable/chunks/IYHzjH-u.js","_app/immutable/chunks/y2AUGcWI.js","_app/immutable/chunks/D5TtrX9z.js","_app/immutable/chunks/DUqvfk82.js","_app/immutable/chunks/BzuisjXd.js","_app/immutable/chunks/DlUCU2Pc.js","_app/immutable/chunks/C_FbWKzR.js"];
export const stylesheets = ["_app/immutable/assets/6.BtgIylkL.css"];
export const fonts = [];
