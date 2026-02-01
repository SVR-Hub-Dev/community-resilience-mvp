#!/usr/bin/env node

import { createConnection } from "net";

const services = [
  { name: "Postgres", host: "localhost", port: 5432 },
  { name: "Ollama", host: "localhost", port: 11434 }
];

const timeoutMs = 60_000;
const retryMs = 1000;

function waitForService({ name, host, port }) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    const tryConnect = () => {
      const socket = createConnection(port, host);
      socket.on("connect", () => {
        socket.end();
        console.log(`✅ ${name} is ready`);
        resolve();
      });
      socket.on("error", () => {
        socket.destroy();
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`❌ Timeout waiting for ${name}`));
        } else {
          setTimeout(tryConnect, retryMs);
        }
      });
    };

    console.log(`⏳ Waiting for ${name} (${host}:${port})...`);
    tryConnect();
  });
}

(async () => {
  try {
    for (const service of services) {
      await waitForService(service);
    }
    process.exit(0);
  } catch (err) {
    console.error(err.message);
    process.exit(1);
  }
})();
