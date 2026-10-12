import { test } from "node:test";
import assert from "node:assert/strict";
import { jobSearchFilters } from "./jobSearchFilters.mjs";

test("remote searches omit even a previously entered location", () => {
  assert.deepEqual(jobSearchFilters("remote", "Boston, MA"), { country: "US", workplace: "remote", location: "" });
});

test("local searches normalize City, ST", () => {
  assert.equal(jobSearchFilters("local", "  St. Louis, mo ").location, "St. Louis, MO");
  assert.equal(jobSearchFilters("local", "Washington, DC").location, "Washington, DC");
});

test("local searches allow an omitted location", () => {
  for (const location of ["", "  "]) {
    assert.deepEqual(jobSearchFilters("local", location), { country: "US", workplace: "local", location: "" });
  }
});

test("setting is required and supplied city/state must be valid", () => {
  for (const location of ["Boston", "Boston, Massachusetts", "Boston, ZZ", ", MA", "123, MA"]) {
    assert.throws(() => jobSearchFilters("local", location), /state abbreviation/);
  }
  assert.throws(() => jobSearchFilters("", ""), /Choose/);
});
