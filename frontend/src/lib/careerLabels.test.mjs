import assert from "node:assert/strict";
import test from "node:test";
import { canonicalizeCareerLabel } from "./careerLabels.mjs";

test("corrects career acronyms including slash and hyphen separated titles", () => {
  assert.equal(canonicalizeCareerLabel("Responsible Ai and Ml"), "Responsible AI and ML");
  assert.equal(canonicalizeCareerLabel("Ai/Ml, Ux/Ui, Nlp and Api-driven design"), "AI/ML, UX/UI, NLP and API-driven design");
});

test("preserves ordinary words, existing acronyms, and proper names", () => {
  assert.equal(canonicalizeCareerLabel("Retail, email, HTML, OpenAI and Python"), "Retail, email, HTML, OpenAI and Python");
  assert.equal(canonicalizeCareerLabel("AI/ML Engineer"), "AI/ML Engineer");
});

test("corrects acronyms throughout multiline career chat responses", () => {
  assert.equal(
    canonicalizeCareerLabel("Explore Ai research and ml engineering.\nTry Ux/Ui design, nlp, or Api-driven projects."),
    "Explore AI research and ML engineering.\nTry UX/UI design, NLP, or API-driven projects.",
  );
});
