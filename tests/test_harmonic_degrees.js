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
    },
    add(name) {
      values.add(name);
    },
    remove(name) {
      values.delete(name);
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

function makeControl() {
  return {
    value: "",
    innerHTML: "",
    listeners: {},
    addEventListener(type, listener) {
      this.listeners[type] = listener;
    }
  };
}

const chords = [
  makeChord("C7M"),
  makeChord("Dm7"),
  makeChord("G7"),
  makeChord("Fm"),
  makeChord("F#dim7"),
  makeChord("G7")
];
const tabPage = {
  dataset: {
    harmonicKey: "C",
    harmonicMode: "major",
    harmonicKeySource: "declared"
  },
  classList: makeClassList()
};
tabPage.classList.add("is-analysis-visible");
const keyLabel = { textContent: "" };
const harmonicTableBody = { innerHTML: "" };
const chordDiagramsContainer = { innerHTML: "" };
const directKeyLabel = { textContent: "" };
const keySignatureAccidentals = { innerHTML: "" };
const keySignature = {
  attributes: {},
  setAttribute(name, value) {
    this.attributes[name] = value;
  }
};
const analysisKeySelect = makeControl();
const analysisModeSelect = makeControl();

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
    if (selector === "[data-chord-diagrams]") return chordDiagramsContainer;
    if (selector === "[data-direct-key]") return directKeyLabel;
    if (selector === "[data-key-signature]") return keySignature;
    if (selector === "[data-key-signature-accidentals]") return keySignatureAccidentals;
    if (selector === "[data-analysis-key]") return analysisKeySelect;
    if (selector === "[data-analysis-mode]") return analysisModeSelect;
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
  ["I7M", "ii7", "V7", "iv", "#iv°7", "V7"]
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
assert.equal((chordDiagramsContainer.innerHTML.match(/class="guitar-chord-card"/g) || []).length, 5);
assert.ok(chordDiagramsContainer.innerHTML.indexOf('data-chord-name="C7M"') <
  chordDiagramsContainer.innerHTML.indexOf('data-chord-name="Dm7"'));
assert.match(chordDiagramsContainer.innerHTML, /data-chord-name="G7" data-frets="[0-9,-]+"/);
assert.match(chordDiagramsContainer.innerHTML, /guitar-neck is-first-position/);
assert.equal(directKeyLabel.textContent, "C");
assert.equal(keySignatureAccidentals.innerHTML, "");
assert.match(keySignature.attributes["aria-label"], /Tom C em clave de sol, sem acidentes/);

function assertKeySignatures(mode, expectedCounts) {
  analysisModeSelect.value = mode;
  analysisModeSelect.listeners.change();
  expectedCounts.forEach(function (expectedCount, pitch) {
    analysisKeySelect.value = String(pitch);
    analysisKeySelect.listeners.change();
    const markup = keySignatureAccidentals.innerHTML;
    assert.equal(
      (markup.match(/key-signature-accidental/g) || []).length,
      Math.abs(expectedCount),
      mode + " pitch " + pitch
    );
    if (expectedCount > 0) assert.match(markup, /♯/);
    if (expectedCount < 0) assert.match(markup, /♭/);
    if (expectedCount === 0) assert.equal(markup, "");
  });
}

assertKeySignatures("major", [0, -5, 2, -3, 4, -1, 6, 1, -4, 3, -2, 5]);
assertKeySignatures("minor", [-3, 4, -1, -6, 1, -4, 3, -2, -7, 0, -5, 2]);

console.log("Graus, desenhos e armaduras harmônicas validados.");
