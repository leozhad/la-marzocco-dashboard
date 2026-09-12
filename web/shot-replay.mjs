// Recorded endpoints drive the replay; intermediate flow is illustrative.
export class ShotReplay {
  constructor() {
    this.shot = null;
    this.status = 'idle';
    this.elapsed = 0;
    this.drainElapsed = 0;
    this.speed = 1;
    this.pausedFrom = 'playing';
  }

  start(shot) {
    if (!Number.isFinite(shot?.extraction_seconds) || shot.extraction_seconds <= 0 ||
        !Number.isFinite(shot?.dose_value) || shot.dose_value < 0) {
      throw new Error('A recorded duration and yield are required to replay a shot.');
    }
    this.shot = { ...shot };
    this.elapsed = 0;
    this.drainElapsed = 0;
    this.status = 'playing';
    return this.snapshot();
  }

  toggle(shot) {
    const same = this.shot?.time === shot?.time &&
      this.shot?.extraction_seconds === shot?.extraction_seconds &&
      this.shot?.dose_value === shot?.dose_value;
    if (!same || this.status === 'idle' || this.status === 'complete') return this.start(shot);
    if (this.status === 'paused') this.status = this.pausedFrom;
    else this.pause();
    return this.snapshot();
  }

  pause() {
    if (this.status === 'playing' || this.status === 'draining') {
      this.pausedFrom = this.status;
      this.status = 'paused';
    }
    return this.snapshot();
  }

  reset() {
    this.status = 'idle';
    this.elapsed = 0;
    this.drainElapsed = 0;
    return this.snapshot();
  }

  setSpeed(value) {
    if (![1, 2, 4].includes(value)) throw new Error('Unsupported replay speed');
    this.speed = value;
  }

  advance(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return this.snapshot();
    let step = seconds * this.speed;
    if (this.status === 'playing') {
      const remaining = this.shot.extraction_seconds - this.elapsed;
      const consumed = Math.min(remaining, step);
      this.elapsed += consumed;
      step -= consumed;
      if (this.elapsed >= this.shot.extraction_seconds) this.status = 'draining';
    }
    if (this.status === 'draining') {
      this.drainElapsed = Math.min(1.2, this.drainElapsed + step);
      if (this.drainElapsed >= 1.2) this.status = 'complete';
    }
    return this.snapshot();
  }

  snapshot() {
    const duration = this.shot?.extraction_seconds || 0;
    const progress = duration ? Math.min(1, this.elapsed / duration) : 0;
    const effective = this.status === 'paused' ? this.pausedFrom : this.status;
    const phase = this.status === 'idle' ? 'Ready to replay' :
      effective === 'playing' && this.elapsed < Math.min(.8, duration * .1) ? 'Paddle on · pump starts' :
      effective === 'playing' ? 'Water through group · extraction' :
      effective === 'draining' ? 'Paddle off · drain valve releases' : 'Shot complete';
    return {
      status: this.status, phase, elapsed: this.elapsed, duration, progress,
      yield: (this.shot?.dose_value || 0) * Math.pow(progress, 1.15),
      targetYield: this.shot?.dose_value || 0, shotTime: this.shot?.time ?? null,
      drainProgress: this.drainElapsed / 1.2, speed: this.speed,
      active: this.status === 'playing' || this.status === 'draining',
      pumpOn: effective === 'playing' && this.status !== 'idle',
    };
  }
}
