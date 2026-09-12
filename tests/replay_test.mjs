import test from 'node:test';
import assert from 'node:assert/strict';
import { ShotReplay } from '../web/shot-replay.mjs';

const shot = { time: 1000, extraction_seconds: 28.9, dose_value: 36 };

test('replay finishes at the selected shot duration and yield, then drains', () => {
  const replay = new ShotReplay();
  replay.start(shot);
  let state = replay.advance(28.9);
  assert.equal(state.status, 'draining');
  assert.equal(state.elapsed, 28.9);
  assert.equal(state.yield, 36);
  assert.equal(state.pumpOn, false);
  state = replay.advance(2);
  assert.equal(state.status, 'complete');
  assert.equal(state.yield, 36);
  assert.equal(state.elapsed, 28.9);
});

test('pause freezes playback and resume continues the same shot', () => {
  const replay = new ShotReplay();
  replay.start(shot);
  replay.advance(5);
  replay.toggle(shot);
  assert.equal(replay.advance(20).elapsed, 5);
  replay.toggle(shot);
  assert.equal(replay.advance(2).elapsed, 7);
});

test('a different selected shot starts a fresh replay with its own endpoints', () => {
  const replay = new ShotReplay();
  replay.start(shot);
  replay.advance(10);
  const next = { time: 2000, extraction_seconds: 33.6, dose_value: 36.3 };
  replay.toggle(next);
  assert.equal(replay.snapshot().elapsed, 0);
  assert.equal(replay.snapshot().shotTime, 2000);
  assert.equal(replay.advance(100).yield, 36.3);
});

test('speed changes advance simulated time without changing recorded endpoints', () => {
  const replay = new ShotReplay();
  replay.setSpeed(4);
  replay.start(shot);
  assert.equal(replay.advance(2).elapsed, 8);
  assert.equal(replay.advance(100).yield, 36);
  replay.reset();
  assert.equal(replay.snapshot().status, 'idle');
  assert.equal(replay.snapshot().yield, 0);
});

test('invalid or unavailable measurements cannot produce fabricated replays', () => {
  const replay = new ShotReplay();
  for (const bad of [{}, { extraction_seconds: 0, dose_value: 36 },
    { extraction_seconds: 20, dose_value: NaN }, { extraction_seconds: 20, dose_value: -1 }]) {
    assert.throws(() => replay.start(bad));
  }
  replay.start(shot);
  assert.equal(replay.advance(-1).elapsed, 0);
  assert.equal(replay.advance(Infinity).elapsed, 0);
  assert.throws(() => replay.setSpeed(10));
});
