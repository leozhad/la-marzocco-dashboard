// Viewed from the operator's position: right is OFF, left starts brewing.
// The angular limits are a visual reconstruction, not factory dimensions.
export const PADDLE_OFF_ANGLE = Math.PI * .22;
export const PADDLE_BREW_ANGLE = -Math.PI * .22;

export function paddleAngle(paddleOn) {
  return paddleOn ? PADDLE_BREW_ANGLE : PADDLE_OFF_ANGLE;
}
