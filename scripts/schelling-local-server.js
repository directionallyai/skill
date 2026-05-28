#!/usr/bin/env node
"use strict";

const http2 = require("node:http2");

const host = process.env.SCHELLING_HOST || "localhost";
const port = Number.parseInt(process.env.SCHELLING_PORT || "9121", 10);

let nextStreamId = 1;

function writeJson(stream, value) {
  stream.write(`${JSON.stringify(value)}\n`);
}

function logJson(value) {
  process.stdout.write(`${JSON.stringify(value)}\n`);
}

function parseLine(line) {
  try {
    return { ok: true, value: JSON.parse(line) };
  } catch (error) {
    return { ok: false, error };
  }
}

const server = http2.createServer();

server.on("stream", (stream, headers) => {
  const method = headers[":method"];
  const path = headers[":path"];

  if (method !== "POST" || path !== "/stream") {
    stream.respond({ ":status": 404, "content-type": "application/x-ndjson" });
    writeJson(stream, {
      kind: "error",
      error: "not_found",
      expected: "POST /stream",
      received_at: new Date().toISOString()
    });
    stream.end();
    return;
  }

  const streamId = nextStreamId++;
  let chunkIndex = 0;
  let lineIndex = 0;
  let buffer = "";

  stream.respond({ ":status": 200, "content-type": "application/x-ndjson" });
  writeJson(stream, {
    kind: "stream_started",
    stream_id: streamId,
    received_at: new Date().toISOString()
  });

  stream.on("data", chunk => {
    chunkIndex += 1;

    const receivedAt = new Date().toISOString();
    const text = chunk.toString("utf8");

    logJson({
      kind: "chunk_received",
      stream_id: streamId,
      chunk_index: chunkIndex,
      received_at: receivedAt,
      byte_length: chunk.length,
      text
    });

    buffer += text;

    let newlineIndex = buffer.indexOf("\n");
    while (newlineIndex !== -1) {
      const rawLine = buffer.slice(0, newlineIndex);
      buffer = buffer.slice(newlineIndex + 1);

      if (rawLine.trim()) {
        lineIndex += 1;
        const parsed = parseLine(rawLine);

        if (parsed.ok) {
          writeJson(stream, {
            kind: "request_received",
            stream_id: streamId,
            chunk_index: chunkIndex,
            line_index: lineIndex,
            received_at: receivedAt,
            op: parsed.value.op || null,
            request: parsed.value
          });
        } else {
          writeJson(stream, {
            kind: "invalid_ndjson",
            stream_id: streamId,
            chunk_index: chunkIndex,
            line_index: lineIndex,
            received_at: receivedAt,
            error: parsed.error.message,
            line: rawLine
          });
        }
      }

      newlineIndex = buffer.indexOf("\n");
    }
  });

  stream.on("end", () => {
    const receivedAt = new Date().toISOString();

    if (buffer.trim()) {
      lineIndex += 1;
      const parsed = parseLine(buffer);

      writeJson(stream, parsed.ok
        ? {
            kind: "request_received",
            stream_id: streamId,
            chunk_index: chunkIndex,
            line_index: lineIndex,
            received_at: receivedAt,
            op: parsed.value.op || null,
            request: parsed.value,
            partial_line: true
          }
        : {
            kind: "invalid_ndjson",
            stream_id: streamId,
            chunk_index: chunkIndex,
            line_index: lineIndex,
            received_at: receivedAt,
            error: parsed.error.message,
            line: buffer,
            partial_line: true
          });
    }

    writeJson(stream, {
      kind: "stream_ended",
      stream_id: streamId,
      received_at: receivedAt,
      chunks: chunkIndex,
      lines: lineIndex
    });
    stream.end();
  });

  stream.on("error", error => {
    logJson({
      kind: "stream_error",
      stream_id: streamId,
      received_at: new Date().toISOString(),
      error: error.message
    });
  });
});

server.on("sessionError", error => {
  logJson({
    kind: "session_error",
    received_at: new Date().toISOString(),
    error: error.message
  });
});

server.on("error", error => {
  logJson({
    kind: "server_error",
    received_at: new Date().toISOString(),
    error: error.message,
    code: error.code || null
  });
  process.exitCode = 1;
});

server.listen(port, host, () => {
  logJson({
    kind: "server_listening",
    received_at: new Date().toISOString(),
    url: `http://${host}:${port}`,
    endpoint: "/stream"
  });
});

function shutdown(signal) {
  logJson({
    kind: "server_shutdown",
    received_at: new Date().toISOString(),
    signal
  });
  server.close(() => process.exit(0));
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
