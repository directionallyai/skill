#!/usr/bin/env node
"use strict";

const http2 = require("node:http2");
const readline = require("node:readline");

const endpoint = process.env.SCHELLING_URL || "http://localhost:9121";
const path = process.env.SCHELLING_PATH || "/stream";

function logError(error) {
  process.stderr.write(`${JSON.stringify({
    kind: "bridge_error",
    received_at: new Date().toISOString(),
    error: error.message
  })}\n`);
}

const client = http2.connect(endpoint);
const stream = client.request({
  ":method": "POST",
  ":path": path,
  "content-type": "application/x-ndjson"
});

stream.setEncoding("utf8");

stream.on("data", chunk => {
  process.stdout.write(chunk);
});

stream.on("error", error => {
  logError(error);
  process.exitCode = 1;
});

stream.on("close", () => {
  client.close();
});

client.on("error", error => {
  logError(error);
  process.exitCode = 1;
});

readline.createInterface({ input: process.stdin }).on("line", line => {
  if (line.trim()) {
    stream.write(`${line}\n`);
  }
});
