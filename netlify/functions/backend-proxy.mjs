const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "content-length",
  "host",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);

function requestPath(event) {
  const rawPath = event.path || "/";
  const prefix = "/.netlify/functions/backend-proxy";
  const path = rawPath.startsWith(prefix) ? rawPath.slice(prefix.length) : rawPath;
  return path || "/";
}

function requestHeaders(event) {
  return Object.fromEntries(
    Object.entries(event.headers || {}).filter(
      ([name]) => !HOP_BY_HOP_HEADERS.has(name.toLowerCase()),
    ),
  );
}

export default async function handler(event) {
  const backendUrl = (process.env.BACKEND_URL || "").replace(/\/$/, "");
  if (!backendUrl) {
    return {
      statusCode: 500,
      headers: { "content-type": "text/plain; charset=utf-8" },
      body: "BACKEND_URL is not configured in Netlify.",
    };
  }

  const target = new URL(`${backendUrl}${requestPath(event)}`);
  for (const [key, value] of Object.entries(event.queryStringParameters || {})) {
    if (value !== undefined && value !== null) target.searchParams.set(key, value);
  }

  const body = event.body
    ? event.isBase64Encoded
      ? Buffer.from(event.body, "base64")
      : event.body
    : undefined;

  let response;
  try {
    response = await fetch(target, {
      method: event.httpMethod,
      headers: requestHeaders(event),
      body: ["GET", "HEAD"].includes(event.httpMethod) ? undefined : body,
      redirect: "manual",
    });
  } catch (error) {
    return {
      statusCode: 502,
      headers: { "content-type": "text/plain; charset=utf-8" },
      body: `Backend unavailable: ${error.message}`,
    };
  }

  const contentType = response.headers.get("content-type") || "application/octet-stream";
  const responseBody = Buffer.from(await response.arrayBuffer());
  const headers = {};
  response.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase()) && key.toLowerCase() !== "set-cookie") {
      headers[key] = value;
    }
  });
  headers["content-type"] = contentType;

  const setCookie = response.headers.getSetCookie?.();
  if (setCookie?.length) headers["set-cookie"] = setCookie;

  return {
    statusCode: response.status,
    headers,
    body: responseBody.toString("base64"),
    isBase64Encoded: true,
  };
}
