// A brew ratio needs dry coffee mass; beverage yield alone cannot determine it.
export const DEFAULT_COFFEE_DOSE_G = null;

export function validDose(value) {
  return Number.isFinite(value) && value > 0 && value <= 50;
}

export function doseForShot(recipe, machine, shotTime) {
  const key = `${machine}:${shotTime}`;
  const specific = recipe?.shots?.[key];
  if (validDose(specific)) return { grams: specific, source: 'this shot' };
  if (validDose(recipe?.defaultDose)) return { grams: recipe.defaultDose, source: 'recipe default' };
  return { grams: null, source: 'not set' };
}

export function brewRatio(yieldGrams, doseGrams) {
  if (!validDose(doseGrams) || !Number.isFinite(yieldGrams) || yieldGrams < 0) return null;
  return yieldGrams / doseGrams;
}

export function ratioLabel(yieldGrams, doseGrams) {
  const value = brewRatio(yieldGrams, doseGrams);
  return value === null ? '—' : `1:${Number(value.toFixed(2))}`;
}
