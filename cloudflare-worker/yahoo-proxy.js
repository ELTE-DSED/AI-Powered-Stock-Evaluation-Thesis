const ALLOWED_HOSTS = new Set([
  "query1.finance.yahoo.com",
  "query2.finance.yahoo.com",
  "finance.yahoo.com",
  "fc.yahoo.com",
  "guce.yahoo.com",
]);

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, User-Agent",
  };
}

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed", { status: 405, headers: corsHeaders() });
    }

    const requestUrl = new URL(request.url);
    const rawTarget = requestUrl.searchParams.get("url");
    if (!rawTarget) {
      return new Response("Missing url query parameter", { status: 400, headers: corsHeaders() });
    }

    let targetUrl;
    try {
      targetUrl = new URL(rawTarget);
    } catch {
      return new Response("Invalid target URL", { status: 400, headers: corsHeaders() });
    }

    if (targetUrl.protocol !== "https:" || !ALLOWED_HOSTS.has(targetUrl.hostname)) {
      return new Response("Target host is not allowed", { status: 403, headers: corsHeaders() });
    }

    const proxyHeaders = new Headers(request.headers);
    proxyHeaders.set(
      "User-Agent",
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    );
    proxyHeaders.set("Accept", request.headers.get("Accept") || "*/*");
    proxyHeaders.delete("Host");
    proxyHeaders.delete("Cookie");

    const upstream = await fetch(targetUrl.toString(), {
      method: request.method,
      headers: proxyHeaders,
      redirect: "follow",
    });

    const responseHeaders = new Headers(upstream.headers);
    for (const [key, value] of Object.entries(corsHeaders())) {
      responseHeaders.set(key, value);
    }
    responseHeaders.delete("set-cookie");

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  },
};
