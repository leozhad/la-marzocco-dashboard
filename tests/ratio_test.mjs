import test from 'node:test';
import assert from 'node:assert/strict';
import { brewRatio, doseForShot, ratioLabel } from '../web/espresso-ratio.mjs';

test('espresso ratio uses grounds in and beverage out, not extraction time', () => {
  assert.equal(brewRatio(36, 18), 2);
  assert.equal(ratioLabel(36, 18), '1:2');
  assert.equal(ratioLabel(36.3, 18), '1:2.02');
  assert.equal(ratioLabel(30, 20), '1:1.5');
});

test('missing, zero, invalid, or negative dry dose never produces a ratio', () => {
  for (const dose of [null, undefined, 0, -1, Infinity, NaN, '18']) {
    assert.equal(brewRatio(36, dose), null);
    assert.equal(ratioLabel(36, dose), '—');
  }
  assert.equal(brewRatio(NaN, 18), null);
});

test('per-shot input overrides the default only for that machine and shot', () => {
  const recipe = { defaultDose: 18, shots: { 'mini:1000': 20 } };
  assert.deepEqual(doseForShot(recipe, 'mini', 1000), { grams: 20, source: 'this shot' });
  assert.deepEqual(doseForShot(recipe, 'mini', 2000), { grams: 18, source: 'recipe default' });
  assert.deepEqual(doseForShot(recipe, 'other', 1000), { grams: 18, source: 'recipe default' });
  assert.deepEqual(doseForShot({}, 'mini', 1000), { grams: null, source: 'not set' });
});
