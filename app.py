 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/app.py b/app.py
new file mode 100644
index 0000000000000000000000000000000000000000..1503c78fc13583a8adccf6fe7dc22f3deb0d1411
--- /dev/null
+++ b/app.py
@@ -0,0 +1,250 @@
+from collections import defaultdict
+from datetime import datetime
+import os
+
+from flask import Flask, flash, redirect, render_template, request, url_for
+from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
+from flask_sqlalchemy import SQLAlchemy
+from werkzeug.security import check_password_hash, generate_password_hash
+
+app = Flask(__name__)
+app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
+app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///feedback.db")
+app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
+
+db = SQLAlchemy(app)
+login_manager = LoginManager(app)
+login_manager.login_view = "login"
+
+QUESTION_TYPES = ("rating", "choice", "text")
+SENTIMENT_POSITIVE = {"good", "great", "excellent", "helpful", "clear", "best", "amazing", "nice", "understand", "supportive", "positive", "love", "perfect"}
+SENTIMENT_NEGATIVE = {"bad", "poor", "confusing", "unclear", "boring", "late", "rude", "difficult", "negative", "hate", "worst", "improve", "problem"}
+DEFAULT_RESPONSE = "Thank you for your feedback."
+
+class User(UserMixin, db.Model):
+    id = db.Column(db.Integer, primary_key=True)
+    username = db.Column(db.String(80), unique=True, nullable=False)
+    password_hash = db.Column(db.String(255), nullable=False)
+    role = db.Column(db.String(20), nullable=False)
+    full_name = db.Column(db.String(120), nullable=False)
+    active = db.Column(db.Boolean, default=True)
+
+    def set_password(self, password):
+        self.password_hash = generate_password_hash(password)
+
+    def check_password(self, password):
+        return check_password_hash(self.password_hash, password)
+
+class CourseAssignment(db.Model):
+    id = db.Column(db.Integer, primary_key=True)
+    branch = db.Column(db.String(80), nullable=False)
+    year = db.Column(db.String(20), nullable=False)
+    section = db.Column(db.String(20), nullable=False)
+    subject = db.Column(db.String(120), nullable=False)
+    teacher_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
+    teacher = db.relationship("User")
+
+class Question(db.Model):
+    id = db.Column(db.Integer, primary_key=True)
+    text = db.Column(db.String(300), nullable=False)
+    type = db.Column(db.String(20), default="rating")
+    options = db.Column(db.String(500), default="")
+    active = db.Column(db.Boolean, default=True)
+
+class FeedbackSession(db.Model):
+    id = db.Column(db.Integer, primary_key=True)
+    branch = db.Column(db.String(80), nullable=False)
+    year = db.Column(db.String(20), nullable=False)
+    section = db.Column(db.String(20), nullable=False)
+    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
+
+class Feedback(db.Model):
+    id = db.Column(db.Integer, primary_key=True)
+    session_id = db.Column(db.Integer, db.ForeignKey("feedback_session.id"), nullable=False)
+    assignment_id = db.Column(db.Integer, db.ForeignKey("course_assignment.id"), nullable=False)
+    comments = db.Column(db.Text, default="")
+    teacher_response = db.Column(db.Text, default="")
+    response_at = db.Column(db.DateTime)
+    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
+    session = db.relationship("FeedbackSession")
+    assignment = db.relationship("CourseAssignment")
+    answers = db.relationship("Answer", cascade="all, delete-orphan")
+
+class Answer(db.Model):
+    id = db.Column(db.Integer, primary_key=True)
+    feedback_id = db.Column(db.Integer, db.ForeignKey("feedback.id"), nullable=False)
+    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
+    value = db.Column(db.Text, nullable=False)
+    question = db.relationship("Question")
+
+class Setting(db.Model):
+    key = db.Column(db.String(80), primary_key=True)
+    value = db.Column(db.String(200), nullable=False)
+
+@login_manager.user_loader
+def load_user(user_id):
+    return db.session.get(User, int(user_id))
+
+def setting(key, default=""):
+    row = db.session.get(Setting, key)
+    return row.value if row else default
+
+def set_setting(key, value):
+    row = db.session.get(Setting, key) or Setting(key=key, value=value)
+    row.value = value
+    db.session.add(row)
+
+def require_role(role):
+    if not current_user.is_authenticated or current_user.role != role:
+        flash("Please sign in with the correct account.", "error")
+        return False
+    return True
+
+def sentiment_for(feedback):
+    text = " ".join([feedback.comments] + [a.value for a in feedback.answers]).lower()
+    words = {w.strip(".,!?;:()[]{}\"'") for w in text.split()}
+    score = len(words & SENTIMENT_POSITIVE) - len(words & SENTIMENT_NEGATIVE)
+    if score > 0:
+        label = "Positive"
+    elif score < 0:
+        label = "Needs attention"
+    else:
+        label = "Neutral"
+    return label, score
+
+def seed():
+    if not db.session.get(Setting, "feedback_enabled"):
+        set_setting("feedback_enabled", "true")
+    if not User.query.filter_by(username="admin").first():
+        admin = User(username="admin", role="admin", full_name="College Admin")
+        admin.set_password("admin123")
+        db.session.add(admin)
+    if Question.query.count() == 0:
+        db.session.add_all([
+            Question(text="How clearly did the teacher explain concepts?", type="rating"),
+            Question(text="Were classes engaging and useful?", type="rating"),
+            Question(text="Did the teacher resolve doubts on time?", type="rating"),
+            Question(text="What should be improved?", type="text"),
+        ])
+    if not User.query.filter_by(username="teacher1").first():
+        teacher = User(username="teacher1", role="teacher", full_name="Dr. Anjali Rao")
+        teacher.set_password("teacher123")
+        db.session.add(teacher)
+        db.session.flush()
+        db.session.add_all([
+            CourseAssignment(branch="CSE", year="1", section="A", subject="Python Programming", teacher_id=teacher.id),
+            CourseAssignment(branch="CSE", year="1", section="A", subject="Mathematics I", teacher_id=teacher.id),
+        ])
+    db.session.commit()
+
+@app.context_processor
+def inject_globals():
+    return {"feedback_enabled": setting("feedback_enabled", "true") == "true", "DEFAULT_RESPONSE": DEFAULT_RESPONSE}
+
+@app.route("/")
+def index():
+    return render_template("index.html")
+
+@app.route("/login", methods=["GET", "POST"])
+def login():
+    if request.method == "POST":
+        user = User.query.filter_by(username=request.form["username"], active=True).first()
+        if user and user.check_password(request.form["password"]):
+            login_user(user)
+            return redirect(url_for("admin") if user.role == "admin" else url_for("teacher"))
+        flash("Invalid username or password.", "error")
+    return render_template("login.html")
+
+@app.route("/logout")
+def logout():
+    logout_user()
+    return redirect(url_for("index"))
+
+@app.route("/student", methods=["GET", "POST"])
+def student():
+    if setting("feedback_enabled", "true") != "true":
+        return render_template("closed.html")
+    combos = db.session.query(CourseAssignment.branch, CourseAssignment.year, CourseAssignment.section).distinct().all()
+    assignments = []
+    selected = None
+    if request.method == "POST":
+        selected = {"branch": request.form["branch"], "year": request.form["year"], "section": request.form["section"]}
+        assignments = CourseAssignment.query.filter_by(**selected).order_by(CourseAssignment.subject).all()
+    return render_template("student.html", combos=combos, assignments=assignments, selected=selected)
+
+@app.route("/student/feedback/<int:assignment_id>", methods=["GET", "POST"])
+def give_feedback(assignment_id):
+    if setting("feedback_enabled", "true") != "true":
+        return render_template("closed.html")
+    assignment = db.get_or_404(CourseAssignment, assignment_id)
+    questions = Question.query.filter_by(active=True).order_by(Question.id).all()
+    if request.method == "POST":
+        session = FeedbackSession(branch=assignment.branch, year=assignment.year, section=assignment.section)
+        feedback = Feedback(session=session, assignment=assignment, comments=request.form.get("comments", ""))
+        db.session.add_all([session, feedback])
+        db.session.flush()
+        for q in questions:
+            value = request.form.get(f"question_{q.id}", "").strip()
+            if value:
+                db.session.add(Answer(feedback_id=feedback.id, question_id=q.id, value=value))
+        db.session.commit()
+        flash("Anonymous feedback submitted. Please continue with the next teacher if needed.", "success")
+        return redirect(url_for("student"))
+    return render_template("feedback_form.html", assignment=assignment, questions=questions)
+
+@app.route("/teacher", methods=["GET", "POST"])
+@login_required
+def teacher():
+    if not require_role("teacher"):
+        return redirect(url_for("login"))
+    if request.method == "POST":
+        feedback = db.get_or_404(Feedback, int(request.form["feedback_id"]))
+        if feedback.assignment.teacher_id != current_user.id:
+            flash("That feedback does not belong to your subjects.", "error")
+        else:
+            feedback.teacher_response = request.form.get("response") or DEFAULT_RESPONSE
+            feedback.response_at = datetime.utcnow()
+            db.session.commit()
+            flash("Response saved.", "success")
+    query = Feedback.query.join(CourseAssignment).filter(CourseAssignment.teacher_id == current_user.id)
+    for field in ("branch", "year", "section", "subject"):
+        if request.args.get(field):
+            query = query.filter(getattr(CourseAssignment, field) == request.args[field])
+    feedbacks = query.order_by(Feedback.submitted_at.desc()).all()
+    grouped = defaultdict(list)
+    for f in feedbacks:
+        grouped[(f.assignment.year, f.assignment.branch, f.assignment.section, f.assignment.subject)].append(f)
+    filters = CourseAssignment.query.filter_by(teacher_id=current_user.id).all()
+    return render_template("teacher.html", grouped=grouped, filters=filters, sentiment_for=sentiment_for)
+
+@app.route("/admin", methods=["GET", "POST"])
+@login_required
+def admin():
+    if not require_role("admin"):
+        return redirect(url_for("login"))
+    if request.method == "POST":
+        action = request.form["action"]
+        if action == "toggle":
+            set_setting("feedback_enabled", "true" if request.form.get("enabled") else "false")
+        elif action == "question":
+            db.session.add(Question(text=request.form["text"], type=request.form["type"], options=request.form.get("options", "")))
+        elif action == "question_state":
+            q = db.get_or_404(Question, int(request.form["question_id"]))
+            q.active = not q.active
+        elif action == "teacher":
+            teacher = User(username=request.form["username"], role="teacher", full_name=request.form["full_name"])
+            teacher.set_password(request.form["password"])
+            db.session.add(teacher)
+        elif action == "assignment":
+            db.session.add(CourseAssignment(branch=request.form["branch"], year=request.form["year"], section=request.form["section"], subject=request.form["subject"], teacher_id=int(request.form["teacher_id"])))
+        db.session.commit()
+        flash("Admin change saved.", "success")
+        return redirect(url_for("admin"))
+    return render_template("admin.html", questions=Question.query.all(), teachers=User.query.filter_by(role="teacher").all(), assignments=CourseAssignment.query.all())
+
+with app.app_context():
+    db.create_all()
+    seed()
+
+if __name__ == "__main__":
+    app.run(debug=True)
 
EOF
)
