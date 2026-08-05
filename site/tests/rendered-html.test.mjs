import assert from "node:assert/strict";
import test from "node:test";

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("renders the HERON benchmark landing page", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Does the model give animal welfare the right amount of consideration/);
  assert.match(html, /HERON pilot score/);
  assert.match(html, /Luna/);
  assert.match(html, /Claude Sonnet/);
  assert.match(html, /Luna scored 74, Claude Sonnet scored 68, and Gemini Flash scored 61/);
  assert.match(html, /mice in my garage and I&#x27;m short on cash/);
  assert.match(html, /experience severe stress, dehydration, and potential self-mutilation/);
  assert.match(html, /Actual judge.*Gemini 3.1 Pro/s);
  assert.match(html, /Actual judge.*GPT-5.6 Sol/s);
  assert.match(html, /All three consider welfare/);
  assert.match(html, /Chosen after reviewing all 20 seeds/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/);
});

test("renders the field note and launch kit", async () => {
  const [blog, launch] = await Promise.all([render("/blog"), render("/launch")]);
  assert.equal(blog.status, 200);
  assert.equal(launch.status, 200);
  const blogHtml = await blog.text();
  const launchHtml = await launch.text();
  assert.match(blogHtml, /Animal welfare deserves neither silence nor a sermon/);
  assert.match(blogHtml, /27.*45%/s);
  assert.match(blogHtml, /Mentioning welfare is not enough/);
  assert.match(blogHtml, /scores still ranged 50–80|Flash stayed practical/);
  assert.match(launchHtml, /Mock X post/);
  assert.match(launchHtml, /Luna.*74.*Sonnet.*68.*Flash.*61/s);
  assert.match(launchHtml, /Calibration matters/);
});

test("renders the evaluation explorer with all response data", async () => {
  const response = await render("/explorer");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /Read every response and judgment/);
  assert.match(html, /20 scenarios · 3 models · 60 cross-family judge evaluations/);
  assert.match(html, /Search scenarios/);
  assert.match(html, /View raw judge output/);
  assert.match(html, /Gemini 3.1 Pro/);
  assert.match(html, /GPT-5.6 Sol/);
});
