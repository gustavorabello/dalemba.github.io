"use strict";

const assert = require("node:assert/strict");

function makeClassList() {
  const values = new Set();
  return {
    toggle(name, force) {
      if (force) values.add(name);
      else values.delete(name);
    },
    contains(name) {
      return values.has(name);
    }
  };
}

function makeChord(text) {
  return {
    textContent: text,
    dataset: {},
    classList: makeClassList(),
    title: ""
  };
}

const chords = [
  makeChord("C7M"),
  makeChord("Dm7"),
  makeChord("G7"),
  makeChord("Fm"),
  makeChord("F#dim7")
];
const tabPage = {
  dataset: {
    harmonicKey: "C",
    harmonicMode: "major",
    harmonicKeySource: "declared"
  },
  classList: makeClassList()
};
const keyLabel = { textContent: "" };
const harmonicTableBody = { innerHTML: "" };

global.getComputedStyle = function () {
  return {
    getPropertyValue() {
      return "16";
    }
  };
};
global.document = {
  body: { dataset: { pageType: "tab", pageSlug: "musica" } },
  documentElement: {},
  querySelector(selector) {
    if (selector === ".page-tab") return tabPage;
    if (selector === "[data-current-key]") return keyLabel;
    if (selector === "[data-harmonic-table]") return harmonicTableBody;
    return null;
  },
  querySelectorAll(selector) {
    if (selector === ".chord") return chords;
    return [];
  }
};

require("../content/static/js/site.js");

assert.deepEqual(
  chords.map((chord) => chord.dataset.harmonicDegree),
  ["I7M", "ii7", "V7", "iv", "#iv°7"]
);
assert.equal(chords[0].classList.contains("is-diatonic"), true);
assert.equal(chords[3].classList.contains("is-outside"), true);
assert.equal(keyLabel.textContent, "C");
assert.match(
  harmonicTableBody.innerHTML,
  /harmonic-table-chord is-diatonic is-scale-chord">C7M/
);
assert.match(
  harmonicTableBody.innerHTML,
  /harmonic-table-chord is-diatonic">Dm7<\/span><span class="harmonic-progression-separator"> – <\/span><span class="harmonic-table-chord is-diatonic">G7/
);
assert.match(
  harmonicTableBody.innerHTML,
  /harmonic-table-chord is-diatonic">Dm7<\/span><span class="harmonic-progression-separator"> – <\/span><span class="harmonic-table-chord is-outside">Db7/
);

console.log("Graus harmônicos validados.");
