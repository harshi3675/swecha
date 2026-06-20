 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/README.md b/README.md
index 1c2802e5d44fb1c48830748f88d8d990848f0fdb..caf3dbaee741a3f8d58af4b4de7af81b2398d916 100644
--- a/README.md
+++ b/README.md
@@ -1,2 +1,28 @@
-# swecha
-its a demo for swecha open source workshop
+# College Student Feedback System
+
+A simple end-to-end anonymous feedback web app for colleges, built with Python, Flask, SQLite, and responsive HTML/CSS.
+
+## Features
+
+- **Student side**: no login, anonymous feedback, branch/year/section selection, subject and teacher list for the selected combination, rating questions, optional text feedback.
+- **Teacher side**: secure login, feedback categorized by year, branch, section, and subject, simple keyword sentiment analysis, optional custom response or default thank-you response.
+- **Admin side**: secure login, no editing of student feedback, no student identity fields, add or disable questions, register teachers, assign subjects, and enable or disable the public feedback link.
+- **Responsive UI**: works on phones, tablets, and laptops.
+
+## Quick start
+
+```bash
+python -m venv .venv
+source .venv/bin/activate
+pip install -r requirements.txt
+python app.py
+```
+
+Open <http://127.0.0.1:5000>.
+
+## Demo accounts
+
+- Admin: `admin` / `admin123`
+- Teacher: `teacher1` / `teacher123`
+
+Change these credentials before using the app in production.
 
EOF
)
