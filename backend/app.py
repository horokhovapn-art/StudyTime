import os, sqlite3, hashlib, secrets, time
from datetime import datetime, date, timedelta
import jwt
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
DB = os.getenv("DB_PATH", "studytime.db")
if SECRET == "dev-secret-change-me": print("WARNING: JWT_SECRET is not set - tokens can be forged. Set it before any public deploy.")
FRONT = os.getenv("FRONTEND_DIR", os.path.join(os.path.dirname(__file__), "..", "frontend"))
START, END = 480, 1320  # study window 08:00-22:00 (minutes)
app = FastAPI(title="StudyTime")

def db():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

with db() as _c:
    _c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE, pw TEXT, limit_h REAL DEFAULT 6);
    CREATE TABLE IF NOT EXISTS busy(id INTEGER PRIMARY KEY, user_id INT, day INT, start INT, end INT, title TEXT);
    CREATE TABLE IF NOT EXISTS tasks(id INTEGER PRIMARY KEY, user_id INT, title TEXT, kind TEXT, hours REAL, deadline_day INT);
    CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY, user_id INT, rating INT, text TEXT, created TEXT);
    CREATE TABLE IF NOT EXISTS slots(id INTEGER PRIMARY KEY, user_id INT, task_id INT, day INT, start INT, end INT, status TEXT DEFAULT 'planned');
    """)
    for tb, col in (("busy", "cat TEXT DEFAULT 'study'"), ("busy", "event_date TEXT"), ("tasks", "cat TEXT DEFAULT 'study'"), ("tasks", "deadline_date TEXT"), ("slots", "week TEXT DEFAULT ''"), ("slots", "pinned INT DEFAULT 0"), ("users", "start_m INT DEFAULT 480"), ("users", "end_m INT DEFAULT 1320")):
        try: _c.execute(f"ALTER TABLE {tb} ADD COLUMN {col}")
        except sqlite3.OperationalError: pass
    _c.execute("UPDATE slots SET week=? WHERE week='' OR week IS NULL", ((date.today() - timedelta(days=date.today().weekday())).isoformat(),))

def hpw(p, salt=None):
    salt = salt or secrets.token_hex(8)
    return salt + "$" + hashlib.pbkdf2_hmac("sha256", p.encode(), salt.encode(), 100000).hex()

def uid(authorization: str = Header("")):
    try:
        i = jwt.decode(authorization.removeprefix("Bearer "), SECRET, algorithms=["HS256"])["sub"]
    except Exception:
        raise HTTPException(401, "Потрібен вхід")
    with db() as c:  # token may outlive the user (e.g. database was reset)
        if not c.execute("SELECT 1 FROM users WHERE id=?", (i,)).fetchone():
            raise HTTPException(401, "Потрібен вхід")
    return i

def token(i): return jwt.encode({"sub": i, "exp": time.time() + 7 * 86400}, SECRET, "HS256")

class Cred(BaseModel): email: str; password: str
class Busy(BaseModel): day: int; start: int; end: int; title: str; cat: str = 'study'; event_date: str | None = None
class NewSlot(BaseModel): task_id: int; day: int; start: int; end: int; week: str
class Move(BaseModel): day: int; start: int; end: int
class Task(BaseModel): title: str; kind: str = "regular"; hours: float; deadline_day: int | None = None; deadline_date: str | None = None; cat: str = 'study'
class Limit(BaseModel): hours: float; start: int = 480; end: int = 1320
class Feedback(BaseModel): rating: int; text: str

def check_date(v):
    if not v: return None
    try: return date.fromisoformat(v).isoformat()
    except ValueError: raise HTTPException(400, "Некоректна дата")

@app.post("/api/signup")
def signup(b: Cred):
    if "@" not in b.email or len(b.password) < 6: raise HTTPException(400, "Email або пароль (мін. 6 символів) некоректні")
    with db() as c:
        try: cur = c.execute("INSERT INTO users(email,pw) VALUES(?,?)", (b.email.lower().strip(), hpw(b.password)))
        except sqlite3.IntegrityError: raise HTTPException(409, "Користувач уже існує")
        return {"token": token(cur.lastrowid)}

@app.post("/api/login")
def login(b: Cred):
    with db() as c:
        r = c.execute("SELECT * FROM users WHERE email=?", (b.email.lower().strip(),)).fetchone()
    if not r or hpw(b.password, r["pw"].split("$")[0]) != r["pw"]: raise HTTPException(401, "Невірний email або пароль")
    return {"token": token(r["id"])}

@app.get("/api/state")
def state(u=Depends(uid)):
    with db() as c:
        q = lambda s: [dict(r) for r in c.execute(s, (u,))]
        return {"busy": q("SELECT * FROM busy WHERE user_id=? ORDER BY day,start"),
                "tasks": q("SELECT * FROM tasks WHERE user_id=?"),
                "slots": q("SELECT s.*,t.title,t.cat FROM slots s JOIN tasks t ON t.id=s.task_id WHERE s.user_id=? ORDER BY day,start"),
                "limit": (ur := c.execute("SELECT limit_h, start_m, end_m FROM users WHERE id=?", (u,)).fetchone())[0], "start": ur[1] or 480, "end": ur[2] or 1320}

@app.post("/api/busy")
def add_busy(b: Busy, u=Depends(uid)):
    if not (0 <= b.day <= 6 and 0 <= b.start < b.end <= 1440): raise HTTPException(400, "Некоректний час")
    ed = check_date(b.event_date)
    with db() as c: c.execute("INSERT INTO busy(user_id,day,start,end,title,cat,event_date) VALUES(?,?,?,?,?,?,?)", (u, b.day, b.start, b.end, b.title, b.cat, ed))
    return {}

@app.delete("/api/busy/{i}")
def del_busy(i: int, u=Depends(uid)):
    with db() as c: c.execute("DELETE FROM busy WHERE id=? AND user_id=?", (i, u))
    return {}

@app.post("/api/tasks")
def add_task(t: Task, u=Depends(uid)):
    if t.hours <= 0 or t.kind not in ("regular", "deadline"): raise HTTPException(400, "Некоректне завдання")
    dd = check_date(t.deadline_date)
    if t.kind == "deadline" and not dd and t.deadline_day is None: raise HTTPException(400, "Вкажіть дату дедлайну")
    with db() as c: c.execute("INSERT INTO tasks(user_id,title,kind,hours,deadline_day,deadline_date,cat) VALUES(?,?,?,?,?,?,?)", (u, t.title, t.kind, t.hours, t.deadline_day, dd, t.cat))
    return {}

@app.delete("/api/tasks/{i}")
def del_task(i: int, u=Depends(uid)):
    with db() as c:
        c.execute("DELETE FROM slots WHERE task_id=? AND user_id=?", (i, u)); c.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (i, u))
    return {}

@app.put("/api/limit")
def limit(l: Limit, u=Depends(uid)):
    st, en = max(0, min(l.start, 1380)), max(60, min(l.end, 1440))
    if en - st < 60: raise HTTPException(400, "???????? ??? ???? ???? ? 1 ???")
    with db() as c: c.execute("UPDATE users SET limit_h=?, start_m=?, end_m=? WHERE id=?", (max(1, min(l.hours, 14)), st, en, u))
    return {}

@app.post("/api/slots/{i}/{status}")
def mark(i: int, status: str, u=Depends(uid)):
    if status not in ("done", "missed", "planned"): raise HTTPException(400, "status")
    with db() as c: c.execute("UPDATE slots SET status=? WHERE id=? AND user_id=?", (status, i, u))
    return {}

@app.put("/api/busy/{i}")
def edit_busy(i: int, b: Busy, u=Depends(uid)):
    if not (0 <= b.day <= 6 and 0 <= b.start < b.end <= 1440): raise HTTPException(400, "Некоректний час")
    ed = check_date(b.event_date)
    with db() as c: c.execute("UPDATE busy SET day=?,start=?,end=?,title=?,cat=?,event_date=? WHERE id=? AND user_id=?", (b.day, b.start, b.end, b.title, b.cat, ed, i, u))
    return {}

@app.put("/api/tasks/{i}")
def edit_task(i: int, t: Task, u=Depends(uid)):
    if t.hours <= 0 or t.kind not in ("regular", "deadline"): raise HTTPException(400, "Некоректне завдання")
    dd = check_date(t.deadline_date)
    if t.kind == "deadline" and not dd and t.deadline_day is None: raise HTTPException(400, "Вкажіть дату дедлайну")
    with db() as c: c.execute("UPDATE tasks SET title=?,kind=?,hours=?,deadline_day=?,deadline_date=?,cat=? WHERE id=? AND user_id=?", (t.title, t.kind, t.hours, t.deadline_day, dd, t.cat, i, u))
    return {}

@app.post("/api/slots")
def new_slot(n: NewSlot, u=Depends(uid)):
    if not (0 <= n.day <= 6 and 0 <= n.start < n.end <= 1440 and len(n.week) == 10): raise HTTPException(400, "Некоректний час")
    with db() as c:
        if not c.execute("SELECT 1 FROM tasks WHERE id=? AND user_id=?", (n.task_id, u)).fetchone(): raise HTTPException(404, "Завдання не знайдено")
        c.execute("INSERT INTO slots(user_id,task_id,day,start,end,week,pinned) VALUES(?,?,?,?,?,?,1)", (u, n.task_id, n.day, n.start, n.end, n.week))
    return {}

@app.put("/api/slots/{i}")
def move_slot(i: int, m: Move, u=Depends(uid)):
    if not (0 <= m.day <= 6 and 0 <= m.start < m.end <= 1440): raise HTTPException(400, "Некоректний час")
    with db() as c: c.execute("UPDATE slots SET day=?,start=?,end=?,pinned=1 WHERE id=? AND user_id=?", (m.day, m.start, m.end, i, u))
    return {}

@app.delete("/api/slots/{i}")
def del_slot(i: int, u=Depends(uid)):
    with db() as c: c.execute("DELETE FROM slots WHERE id=? AND user_id=?", (i, u))
    return {}

def place(c, u, t, rem, days, rng, per):
    for k in rng:
        D, got = days[k], 0
        for g in D["gaps"]:
            while rem > 0 and D["cap"] > 0 and got < per and g[1] - g[0] >= 30:
                n = min(90, g[1] - g[0], rem, D["cap"], per - got)
                if n <= 0: break
                c.execute("INSERT INTO slots(user_id,task_id,day,start,end,week) VALUES(?,?,?,?,?,?)", (u, t["id"], D["d"], g[0], g[0] + n, D["wk"]))
                g[0] += n + 10; D["cap"] -= n; got += n; rem -= n
    return rem

def fill(c, u, t, rem, days, rng):
    rem = place(c, u, t, rem, days, rng, -(-rem // len(rng) // 30) * 30 or 30)
    return place(c, u, t, rem, days, rng, 10**6)

@app.post("/api/replan")
def replan(u=Depends(uid)):
    """Smart Fit: plan from today up to the last deadline (up to 12 weeks ahead) in the free windows, respecting the daily limit."""
    now = datetime.now(); today = date.today(); td = today.weekday(); nm = -(-(now.hour * 60 + now.minute) // 5) * 5
    mon = today - timedelta(days=td); wk = mon.isoformat()
    unplaced, overdue = {}, []
    with db() as c:
        c.execute("UPDATE slots SET status='missed' WHERE user_id=? AND status='planned' AND (week<? OR (week=? AND (day<? OR (day=? AND end<=?))))", (u, wk, wk, td, td, nm))
        c.execute("DELETE FROM slots WHERE user_id=? AND pinned=0 AND status='planned' AND (week>? OR (week=? AND (day>? OR (day=? AND start>=?))))", (u, wk, wk, td, td, nm))
        uc = c.execute("SELECT limit_h, start_m, end_m FROM users WHERE id=?", (u,)).fetchone()
        lim, st_m, en_m = uc[0] * 60, (uc[1] or START), (uc[2] or END)
        tasks = c.execute("SELECT * FROM tasks WHERE user_id=?", (u,)).fetchall()
        def due(t):
            if t["deadline_date"]:
                try: return date.fromisoformat(t["deadline_date"])
                except ValueError: pass
            if t["kind"] == "deadline" and t["deadline_day"] is not None: return mon + timedelta(days=t["deadline_day"])
            return None
        far = max([x for x in map(due, tasks) if x] or [today])
        H = min(max((far - mon).days // 7 + 1, 1), 12)
        K = H * 7 - td
        days = {}
        for k in range(K):
            day = today + timedelta(days=k); d = day.weekday(); w = (day - timedelta(days=d)).isoformat()
            iv = [(r["start"], r["end"]) for r in c.execute("SELECT start,end FROM busy WHERE user_id=? AND day=? AND (event_date IS NULL OR event_date='' OR event_date=?)", (u, d, day.isoformat()))]
            sl = c.execute("SELECT start,end FROM slots WHERE user_id=? AND day=? AND week=? AND status!='missed'", (u, d, w)).fetchall()
            iv += [(r["start"], r["end"]) for r in sl]
            if k == 0: iv.append((0, nm))
            gaps, cur = [], st_m
            for a, b in sorted(iv):
                if a - cur >= 30: gaps.append([cur, a])
                cur = max(cur, b)
            if en_m - cur >= 30: gaps.append([cur, en_m])
            days[k] = {"d": d, "wk": w, "gaps": gaps, "cap": max(0, lim - sum(r["end"] - r["start"] for r in sl))}
        for t in sorted(tasks, key=lambda t: (due(t) is None, due(t) or date.max)):
            dd, total = due(t), int(t["hours"] * 60)
            if dd is None:
                for w in range(H):
                    used = c.execute("SELECT COALESCE(SUM(end-start),0) FROM slots WHERE task_id=? AND status IN('done','planned') AND week=?", (t["id"], (mon + timedelta(days=7 * w)).isoformat())).fetchone()[0]
                    rng, rem = range(max(0, 7 * w - td), min(K, 7 * w + 7 - td)), total - used
                    if rem > 0 and len(rng):
                        rem = fill(c, u, t, rem, days, rng)
                        if rem > 0: unplaced[t["title"]] = unplaced.get(t["title"], 0) + rem
            else:
                rem = total - c.execute("SELECT COALESCE(SUM(end-start),0) FROM slots WHERE task_id=? AND status IN('done','planned')", (t["id"],)).fetchone()[0]
                if rem <= 0: continue
                if dd < today: overdue.append(t["title"])
                rem = fill(c, u, t, rem, days, range(0, min(max((dd - today).days, 0), K - 1) + 1))
                if rem > 0: unplaced[t["title"]] = unplaced.get(t["title"], 0) + rem
    return {"unplaced": [{"title": k, "minutes": v} for k, v in unplaced.items()], "overdue": overdue}


@app.post("/api/feedback")
def feedback(f: Feedback, u=Depends(uid)):
    if not (1 <= f.rating <= 5) or not f.text.strip(): raise HTTPException(400, "Вкажіть оцінку й текст")
    with db() as c: c.execute("INSERT INTO feedback(user_id,rating,text,created) VALUES(?,?,?,?)", (u, f.rating, f.text.strip()[:2000], datetime.now().isoformat(timespec="minutes")))
    return {}

app.mount("/", StaticFiles(directory=FRONT, html=True), name="front")
