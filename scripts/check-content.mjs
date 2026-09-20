import { existsSync, readFileSync, statSync } from 'node:fs';
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
for (const path of ['judge/OPERATIONS.md', 'judge/preflight.sh', 'judge/run_reference.sh', 'judge/roster.example.csv', 'judge/reference/README.md']) {
  requireFile(path, 'Judge machine handoff');
}

const topic00 = course.lectures.find((lecture) => lecture.id === '00');
if (topic00?.materials?.evidence === 'ready') {
  const run = 'seminars/runs/2026-09-20-topic-00-metric-contract-v2';
  requireFile(`${run}/README.md`, 'Topic 00 canonical operator note');
  requireFile(`${run}/results.json`, 'Topic 00 canonical raw results');
  requireFile(`${run}/naive.log`, 'Topic 00 canonical naive log');
  requireFile(`${run}/vllm.log`, 'Topic 00 canonical vLLM log');
  try {
    const result = JSON.parse(readFileSync(join(root, run, 'results.json'), 'utf8'));
    if (result.provenance?.metric_contract !== 2) errors.push('Topic 00 evidence: metric contract is not v2');
    if (!/^[0-9a-f]{40}$/.test(result.provenance?.course_commit || '')) errors.push('Topic 00 evidence: immutable course commit missing');
    if (!/^[0-9a-f]{40}$/.test(result.provenance?.model_revision || '')) errors.push('Topic 00 evidence: immutable model revision missing');
    if (!Array.isArray(result.raw_requests) || result.raw_requests.length !== 630) errors.push('Topic 00 evidence: expected 630 raw request records');
    if (!result.summary?.pipeline?.['64'] || !result.summary?.vLLM?.['64']) errors.push('Topic 00 evidence: 64-client summary missing');
    for (const server of ['pipeline', 'vLLM']) {
      for (const concurrency of [1, 8, 32, 64]) {
        const rows = result.raw_requests?.filter((row) => row.server === server && row.concurrency === concurrency) || [];
        const aggregate = result.summary?.[server]?.[String(concurrency)];
        if (rows.length !== concurrency * 3) errors.push(`Topic 00 evidence: ${server} c=${concurrency} raw count mismatch`);
        if (aggregate && (aggregate.attempted !== rows.length || aggregate.ok !== rows.filter((row) => row.ok).length || aggregate.failed !== rows.filter((row) => !row.ok).length)) {
          errors.push(`Topic 00 evidence: ${server} c=${concurrency} aggregate does not reconcile with raw records`);
        }
      }
    }
    if (result.raw_requests?.some((row) => !row.request_id || !row.started_utc || typeof row.ok !== 'boolean' || typeof row.latency !== 'number')) {
      errors.push('Topic 00 evidence: a raw request is missing required audit fields');
    }
    if (result.raw_requests?.some((row) => row.ok ? typeof row.ttft !== 'number' : row.ttft !== null)) {
      errors.push('Topic 00 evidence: TTFT population mixes successful and failed requests');
    }
    for (const log of ['naive.log', 'vllm.log']) {
      if (existsSync(join(root, run, log)) && statSync(join(root, run, log)).size === 0) errors.push(`Topic 00 evidence: ${log} is empty`);
    }
  } catch (error) {
    errors.push(`Topic 00 evidence: invalid results.json (${error.message})`);
  }
}

if (errors.length) {
  console.error(errors.map((item) => `- ${item}`).join('\n'));
  process.exit(1);
}
console.log(`[content-check] ${course.lectures.length} published topics and ${portal.glossary.length} glossary terms passed`);
