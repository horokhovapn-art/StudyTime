"""Usage numbers for the report. Run from backend/:  python stats.py  (uses DB_PATH like the app)."""
import os, sqlite3
c = sqlite3.connect(os.getenv("DB_PATH", "studytime.db"))
q = lambda s: c.execute(s).fetchone()[0]
print("Registered users:            ", q("SELECT COUNT(*) FROM users"))
print("...added a fixed event:      ", q("SELECT COUNT(DISTINCT user_id) FROM busy"))
print("...added a task:             ", q("SELECT COUNT(DISTINCT user_id) FROM tasks"))
print("...got a generated plan:     ", q("SELECT COUNT(DISTINCT user_id) FROM slots"))
print("Blocks done / missed:        ", q("SELECT COUNT(*) FROM slots WHERE status='done'"), "/", q("SELECT COUNT(*) FROM slots WHERE status='missed'"))
n = q("SELECT COUNT(*) FROM feedback")
print("Feedback entries:", n, "| average rating:", round(q("SELECT AVG(rating) FROM feedback") or 0, 2))
for r in c.execute("SELECT created, rating, text FROM feedback ORDER BY id"): print(f"  [{r[0]}] {r[1]}/5  {r[2]}")
