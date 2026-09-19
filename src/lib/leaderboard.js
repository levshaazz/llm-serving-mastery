// leaderboard.js — the judge's files are the only source of the board:
//   judge/thresholds/round-NN.json   published bars (written by judge/make_thresholds.py or by hand)
//   data/leaderboard/round-NN.json   scored rounds (written by judge/score.py)
const th = import.meta.glob('../../judge/thresholds/round-*.json', { eager: true, import: 'default' });
const lb = import.meta.glob('../../data/leaderboard/round-*.json', { eager: true, import: 'default' });

const byRound = (m) => Object.values(m).sort((a, b) => a.round - b.round);
export const thresholds = byRound(th);
export const rounds = byRound(lb);

// Running totals per student across scored rounds: points (of 40) and Overdrive.
export function standings() {
  const acc = new Map();
  for (const r of rounds) {
    for (const row of r.rows) {
      const s = acc.get(row.student) || { student: row.student, points: 0, overdrive: 0, rounds: 0 };
      s.points += row.points || 0; s.overdrive += row.overdrive || 0; s.rounds += 1;
      acc.set(row.student, s);
    }
  }
  return [...acc.values()].sort((a, b) => b.points - a.points || b.overdrive - a.overdrive);
}
