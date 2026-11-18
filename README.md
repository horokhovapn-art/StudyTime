# StudyTime

## Team
Sofiia Volvach, Sofiia Horokhova

**An adaptive study planner for students.** Enter your fixed schedule (lectures, work, sleep) and your goals
(weekly targets and deadlines), and StudyTime places study time into your free windows automatically.

### Live demo: [https://63.176.50.123.nip.io](https://63.176.50.123.nip.io)

## Features
- Sign up and sign in; every user sees only their own data
- Weekly calendar with categories; fixed events repeat weekly or happen on a single date
- Tasks: weekly goals or deadlines on a specific date
- Smart Fit planning that respects your working hours, a daily limit and a minimum session length,
  and plans ahead up to the last deadline
- Drag blocks to move them, or drag a task into the calendar
- Built-in feedback form

## How it works

**1. Set your rules.** Choose your working hours (default 08:00–22:00), how many hours you can study per day
(default 6) and the minimum length of one study session (default 45 minutes).

**2. Add what is fixed.** Lectures, work, sleep and training are fixed events. They repeat every week or
happen on a single date, and StudyTime never plans over them.

**3. Add what you need to do.** There are two kinds of tasks:
- a **weekly goal** — "N hours every week" with no deadline;
- a **deadline task** — "N hours in total by a specific date".

**4. Press Replan.** StudyTime looks at your free time (your working day minus fixed events and blocks
already in the calendar; for today, only the time that is still ahead) and fills it with study blocks:
- tasks with the nearest deadline are planned first, weekly goals after them;
- a deadline task is spread evenly over the days until its date — for example, 7 hours with a deadline
  in 7 days becomes about 1 hour per day, across this week and the next;
- a weekly goal is spread over the days of each week;
- one block lasts between the minimum session and 90 minutes, with a short break after it, and the daily
  limit is never exceeded;
- planning reaches as far as the last deadline (up to 12 weeks ahead); without deadlines it plans the
  current week.

**5. Do the work and keep the plan honest.**
- Tick a block when it is done — it counts toward the task.
- If you miss a block (or forget to mark it and its time has passed), its hours go back into the pool and
  are planned again on the next Replan. Unfinished hours of a deadline task always carry over; unfinished
  hours of a weekly goal do not move to the next week.
- If something does not fit, you get a warning with the number of hours left. Overdue tasks are flagged and
  planned for today.

**6. Stay in control.** Drag a block to another time, or drag a task from the sidebar into the calendar.
Blocks you place by hand are pinned: Replan never moves them, and they count toward your daily limit.
Nothing changes in the plan until you press Replan.

## Built with
Python (FastAPI), SQLite, plain HTML/CSS/JavaScript, Docker, hosted on AWS.

## Repository structure
- `backend/` — the server: accounts, API and the planning algorithm
- `frontend/` — the web interface
- `infra/` — Docker files used for deployment
- `docs/` — screenshots and project materials

## Deployment
The demo runs in Docker on an AWS server with HTTPS. To deploy your own copy, use the files in `infra/`
(set `DOMAIN` and `JWT_SECRET` in `infra/.env`, then run `docker compose up -d --build` in that folder).
