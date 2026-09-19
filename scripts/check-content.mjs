import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import course from '../data/course.json' with { type: 'json' };
import portal from '../data/portal.json' with { type: 'json' };

const root = join(import.meta.dirname, '..');
const errors = [];
const allowed = new Set(['ready', 'planned', 'needs-rehearsal', 'student-generated']);
const requireFile = (path, label) => {
  if (!path || !existsSync(join(root, path))) errors.push(`${label}: missing ${path || '(unset)'}`);
};

for (const lecture of course.lectures) {
  const deckSource = lecture.deckFile?.replace(/\.html$/, '');
  requireFile(`${deckSource}/parts/00-head.html`, `Topic ${lecture.id} slide source`);
  if (lecture.materials?.lab === 'ready') requireFile(lecture.notebook, `Topic ${lecture.id} lab`);
  for (const [kind, state] of Object.entries(lecture.materials || {})) {
    if (!allowed.has(state)) errors.push(`Topic ${lecture.id} ${kind}: unknown readiness ${state}`);
  }
  if (!portal.topics.some((topic) => topic.n === lecture.topic)) errors.push(`Topic ${lecture.id}: missing topic-page data`);
}

for (const topic of portal.topics) {
  if (!course.lectures.some((lecture) => lecture.topic === topic.n)) errors.push(`Topic-page ${topic.id}: no lecture record`);
  for (const key of ['outcomes', 'session', 'artifacts', 'acceptance', 'reading']) {
    if (!Array.isArray(topic[key]) || topic[key].length === 0) errors.push(`Topic-page ${topic.id}: empty ${key}`);
  }
}

const judgeConfig = readFileSync(join(root, 'judge/config.yaml'), 'utf8');
const judgeSource = readFileSync(join(root, 'judge/run_submission.py'), 'utf8');
if (!/startup_timeout_s:\s*1800/.test(judgeConfig)) errors.push('Judge startup budget is not 1800 seconds');
if (!/PhaseDeadline\(deadline,\s*cfg\["server"\]\["startup_timeout_s"\]/.test(judgeSource)) errors.push('Judge does not share the startup phase deadline');
if (existsSync(join(root, 'seminars/runs/00-live-demo-rehearsal-2026-09-19.txt'))) errors.push('Legacy rehearsal still has a canonical-looking filename');
requireFile('seminars/runs/00-live-demo-rehearsal-2026-09-19.legacy-invalid.txt', 'Legacy rehearsal audit trail');

if (errors.length) {
  console.error(errors.map((item) => `- ${item}`).join('\n'));
  process.exit(1);
}
console.log(`[content-check] ${course.lectures.length} published topics and ${portal.glossary.length} glossary terms passed`);
