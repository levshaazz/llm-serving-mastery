import portalData from '../../data/portal.json';

export const portal = portalData;

export const MATERIAL_LABELS = {
  slides: 'Slides',
  lab: 'Lab',
  assignment: 'Assignment',
  reading: 'Reading',
  evidence: 'Evidence',
};

export function overallReadiness(materials = {}) {
  const values = Object.values(materials);
  if (!values.length) return 'planned';
  return values.every((value) => value === 'ready') ? 'ready' : 'partial';
}

export function topicPath(lang, topic) {
  return `/${lang}/topics/${String(topic).padStart(2, '0')}/`;
}
