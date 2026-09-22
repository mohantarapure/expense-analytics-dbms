
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import date
import csv, io, sqlite3
from database import init_db, get_connection
from analytics import spending_risk

app = Flask(__name__)
app.secret_key = "local-development-secret-change-if-deployed"

CATEGORIES = ["Food","Travel","Shopping","Bills","Education","Health","Entertainment","Other"]
PAYMENT_MODES = ["Cash","UPI","Credit Card","Debit Card","Bank Transfer"]

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

def current_user_id():
    return session["user_id"]

def get_categories(conn):
    return conn.execute("SELECT * FROM categories ORDER BY category_name").fetchall()

def get_modes(conn):
    return conn.execute("SELECT * FROM payment_modes ORDER BY mode_name").fetchall()

def seed_defaults():
    conn = get_connection()
    try:
        for x in CATEGORIES:
            conn.execute("INSERT OR IGNORE INTO categories(category_name) VALUES(?)",(x,))
        for x in PAYMENT_MODES:
            conn.execute("INSERT OR IGNORE INTO payment_modes(mode_name) VALUES(?)",(x,))
        conn.commit()
    finally:
        conn.close()

@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or "@" not in email or len(password) < 6:
            flash("Enter a valid name/email and password of at least 6 characters.", "danger")
            return render_template("register.html")
        conn = get_connection()
        try:
            conn.execute("INSERT INTO users(name,email,password) VALUES(?,?,?)",
                         (name,email,generate_password_hash(password)))
            conn.commit()
            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
        finally:
            conn.close()
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        conn=get_connection()
        try:
            user=conn.execute("SELECT * FROM users WHERE email=?",(email,)).fetchone()
        finally:
            conn.close()
        if user and check_password_hash(user["password"],password):
            session["user_id"]=user["user_id"]; session["user_name"]=user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.","danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.","success")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    uid=current_user_id(); month=date.today().strftime("%Y-%m")
    conn=get_connection()
    try:
        total=conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=?",(uid,)).fetchone()[0]
        month_total=conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=? AND substr(expense_date,1,7)=?",(uid,month)).fetchone()[0]
        budget=conn.execute("SELECT COALESCE(SUM(amount),0) FROM budgets WHERE user_id=? AND month_year=?",(uid,month)).fetchone()[0]
        count=conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?",(uid,)).fetchone()[0]
        top=conn.execute("""SELECT c.category_name,SUM(e.amount) total FROM expenses e
            JOIN categories c ON c.category_id=e.category_id WHERE e.user_id=?
            GROUP BY c.category_id ORDER BY total DESC LIMIT 1""",(uid,)).fetchone()
        recent=conn.execute("""SELECT e.*,c.category_name,p.mode_name FROM expenses e
            JOIN categories c ON c.category_id=e.category_id JOIN payment_modes p ON p.payment_mode_id=e.payment_mode_id
            WHERE e.user_id=? ORDER BY e.expense_date DESC,e.expense_id DESC LIMIT 5""",(uid,)).fetchall()
        category=conn.execute("""SELECT c.category_name label,ROUND(SUM(e.amount),2) total
            FROM expenses e JOIN categories c ON c.category_id=e.category_id
            WHERE e.user_id=? GROUP BY c.category_id ORDER BY total DESC""",(uid,)).fetchall()
        monthly=conn.execute("""SELECT substr(expense_date,1,7) label,ROUND(SUM(amount),2) total
            FROM expenses WHERE user_id=? GROUP BY substr(expense_date,1,7) ORDER BY label""",(uid,)).fetchall()
    finally: conn.close()
    risk=spending_risk(month_total,budget)
    return render_template("dashboard.html",total=total,month_total=month_total,budget=budget,count=count,
                           top=top,risk=risk,recent=recent,category=category,monthly=monthly,month=month)

@app.route("/expenses")
@login_required
def expenses():
    uid=current_user_id(); conn=get_connection()
    try:
        cats=get_categories(conn); modes=get_modes(conn)
        q="""SELECT e.*,c.category_name,p.mode_name FROM expenses e
             JOIN categories c ON c.category_id=e.category_id
             JOIN payment_modes p ON p.payment_mode_id=e.payment_mode_id
             WHERE e.user_id=?"""
        params=[uid]
        category=request.args.get("category",""); mode=request.args.get("mode","")
        start=request.args.get("start",""); end=request.args.get("end","")
        minamt=request.args.get("min_amount",""); maxamt=request.args.get("max_amount","")
        if category: q+=" AND e.category_id=?"; params.append(category)
        if mode: q+=" AND e.payment_mode_id=?"; params.append(mode)
        if start: q+=" AND e.expense_date>=?"; params.append(start)
        if end: q+=" AND e.expense_date<=?"; params.append(end)
        if minamt: q+=" AND e.amount>=?"; params.append(minamt)
        if maxamt: q+=" AND e.amount<=?"; params.append(maxamt)
        q+=" ORDER BY e.expense_date DESC,e.expense_id DESC"
        rows=conn.execute(q,params).fetchall()
    finally: conn.close()
    return render_template("expenses.html",expenses=rows,categories=cats,modes=modes,
                           filters=request.args)

def expense_form(template, expense=None):
    conn=get_connection()
    try:
        cats=get_categories(conn); modes=get_modes(conn)
    finally: conn.close()
    return render_template(template, expense=expense,categories=cats,modes=modes,today=date.today().isoformat())

@app.route("/expenses/add",methods=["GET","POST"])
@login_required
def add_expense():
    if request.method=="POST":
        try:
            category=int(request.form["category"]); mode=int(request.form["mode"])
            amount=float(request.form["amount"]); desc=request.form.get("description","").strip()
            dt=request.form["expense_date"]
            if amount<=0 or not dt: raise ValueError
        except (ValueError,KeyError):
            flash("Please enter valid expense details.","danger"); return expense_form("add_expense.html")
        conn=get_connection()
        try:
            conn.execute("""INSERT INTO expenses(user_id,category_id,payment_mode_id,amount,description,expense_date)
                            VALUES(?,?,?,?,?,?)""",(current_user_id(),category,mode,amount,desc,dt))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Invalid category/payment mode.","danger"); return expense_form("add_expense.html")
        finally: conn.close()
        flash("Expense added.","success"); return redirect(url_for("expenses"))
    return expense_form("add_expense.html")

@app.route("/expenses/<int:eid>/edit",methods=["GET","POST"])
@login_required
def edit_expense(eid):
    conn=get_connection()
    try:
        expense=conn.execute("SELECT * FROM expenses WHERE expense_id=? AND user_id=?",(eid,current_user_id())).fetchone()
    finally: conn.close()
    if not expense: flash("Expense not found.","danger"); return redirect(url_for("expenses"))
    if request.method=="POST":
        try:
            category=int(request.form["category"]); mode=int(request.form["mode"]); amount=float(request.form["amount"])
            dt=request.form["expense_date"]; desc=request.form.get("description","").strip()
            if amount<=0 or not dt: raise ValueError
        except (ValueError,KeyError):
            flash("Please enter valid details.","danger"); return expense_form("edit_expense.html",expense)
        conn=get_connection()
        try:
            conn.execute("""UPDATE expenses SET category_id=?,payment_mode_id=?,amount=?,description=?,expense_date=?
                            WHERE expense_id=? AND user_id=?""",(category,mode,amount,desc,dt,eid,current_user_id()))
            conn.commit()
        finally: conn.close()
        flash("Expense updated.","success"); return redirect(url_for("expenses"))
    return expense_form("edit_expense.html",expense)

@app.route("/expenses/<int:eid>/delete",methods=["POST"])
@login_required
def delete_expense(eid):
    conn=get_connection()
    try:
        cur=conn.execute("DELETE FROM expenses WHERE expense_id=? AND user_id=?",(eid,current_user_id()))
        conn.commit()
        flash("Expense deleted." if cur.rowcount else "Expense not found.","success" if cur.rowcount else "warning")
    except Exception:
        conn.rollback(); flash("Could not delete expense.","danger")
    finally: conn.close()
    return redirect(url_for("expenses"))

@app.route("/budgets",methods=["GET","POST"])
@login_required
def budgets():
    conn=get_connection()
    try:
        cats=get_categories(conn)
        if request.method=="POST":
            cat=int(request.form["category"]); amount=float(request.form["amount"]); month=request.form["month_year"]
            if amount<=0: raise ValueError
            conn.execute("INSERT INTO budgets(user_id,category_id,amount,month_year) VALUES(?,?,?,?)",
                         (current_user_id(),cat,amount,month))
            conn.commit(); flash("Budget added.","success")
    except ValueError: conn.rollback(); flash("Enter a valid positive amount.","danger")
    except sqlite3.IntegrityError: conn.rollback(); flash("A budget for this category/month already exists.","danger")
    finally: conn.close()
    conn=get_connection()
    try:
        rows=conn.execute("""SELECT b.*,c.category_name,
            COALESCE((SELECT SUM(e.amount) FROM expenses e WHERE e.user_id=b.user_id AND e.category_id=b.category_id AND substr(e.expense_date,1,7)=b.month_year),0) actual
            FROM budgets b JOIN categories c ON c.category_id=b.category_id
            WHERE b.user_id=? ORDER BY b.month_year DESC,c.category_name""",(current_user_id(),)).fetchall()
    finally: conn.close()
    return render_template("budget.html",budgets=rows,categories=cats,today=date.today().strftime("%Y-%m"))

@app.route("/budgets/<int:bid>/delete",methods=["POST"])
@login_required
def delete_budget(bid):
    conn=get_connection()
    try:
        conn.execute("DELETE FROM budgets WHERE budget_id=? AND user_id=?",(bid,current_user_id())); conn.commit()
        flash("Budget deleted.","success")
    finally: conn.close()
    return redirect(url_for("budgets"))

@app.route("/master-data",methods=["GET","POST"])
@login_required
def master_data():
    conn=get_connection()
    try:
        if request.method=="POST":
            typ=request.form["type"]; name=request.form["name"].strip()
            table="categories" if typ=="category" else "payment_modes"
            col="category_name" if typ=="category" else "mode_name"
            if not name: raise ValueError
            conn.execute(f"INSERT INTO {table}({col}) VALUES(?)",(name,)); conn.commit(); flash("Master data added.","success")
    except ValueError: conn.rollback(); flash("Name is required.","danger")
    except sqlite3.IntegrityError: conn.rollback(); flash("That value already exists.","danger")
    finally: conn.close()
    conn=get_connection()
    try: cats=get_categories(conn); modes=get_modes(conn)
    finally: conn.close()
    return render_template("master_data.html",categories=cats,modes=modes)

@app.route("/master-data/delete/<string:typ>/<int:item_id>",methods=["POST"])
@login_required
def delete_master(typ,item_id):
    table="categories" if typ=="category" else "payment_modes"
    key="category_id" if typ=="category" else "payment_mode_id"
    conn=get_connection()
    try:
        conn.execute(f"DELETE FROM {table} WHERE {key}=?",(item_id,)); conn.commit(); flash("Master data deleted.","success")
    except sqlite3.IntegrityError:
        conn.rollback(); flash("Cannot delete: this item is used by existing records.","danger")
    finally: conn.close()
    return redirect(url_for("master_data"))

@app.route("/reports")
@login_required
def reports():
    uid=current_user_id(); conn=get_connection()
    try:
        category=conn.execute("""SELECT c.category_name,COUNT(e.expense_id) transactions,
            ROUND(COALESCE(SUM(e.amount),0),2) total,ROUND(COALESCE(AVG(e.amount),0),2) average
            FROM categories c LEFT JOIN expenses e ON e.category_id=c.category_id AND e.user_id=?
            GROUP BY c.category_id HAVING total > 0 ORDER BY total DESC""",(uid,)).fetchall()
        monthly=conn.execute("""SELECT substr(expense_date,1,7) month,COUNT(*) transactions,ROUND(SUM(amount),2) total
            FROM expenses WHERE user_id=? GROUP BY month ORDER BY month DESC""",(uid,)).fetchall()
        modes=conn.execute("""SELECT p.mode_name,COUNT(*) transactions,ROUND(SUM(e.amount),2) total
            FROM expenses e JOIN payment_modes p ON p.payment_mode_id=e.payment_mode_id
            WHERE e.user_id=? GROUP BY p.payment_mode_id ORDER BY total DESC""",(uid,)).fetchall()
        budget=conn.execute("""SELECT b.month_year,c.category_name,b.amount budget,
            ROUND(COALESCE(SUM(e.amount),0),2) actual,ROUND(b.amount-COALESCE(SUM(e.amount),0),2) remaining
            FROM budgets b JOIN categories c ON c.category_id=b.category_id
            LEFT JOIN expenses e ON e.user_id=b.user_id AND e.category_id=b.category_id AND substr(e.expense_date,1,7)=b.month_year
            WHERE b.user_id=? GROUP BY b.budget_id ORDER BY b.month_year DESC""",(uid,)).fetchall()
        high=conn.execute("""SELECT e.expense_date,e.amount,e.description,c.category_name
            FROM expenses e JOIN categories c ON c.category_id=e.category_id
            WHERE e.user_id=? AND e.amount>(SELECT AVG(amount) FROM expenses WHERE user_id=?)
            ORDER BY e.amount DESC LIMIT 10""",(uid,uid)).fetchall()
    finally: conn.close()
    return render_template("reports.html",category=category,monthly=monthly,modes=modes,budget=budget,high=high)

@app.route("/export/<string:kind>")
@login_required
def export_csv(kind):
    uid=current_user_id(); conn=get_connection()
    try:
        if kind=="expenses":
            rows=conn.execute("""SELECT e.expense_date,c.category_name,p.mode_name,e.amount,e.description
                FROM expenses e JOIN categories c ON c.category_id=e.category_id JOIN payment_modes p ON p.payment_mode_id=e.payment_mode_id
                WHERE e.user_id=? ORDER BY e.expense_date DESC""",(uid,)).fetchall()
            headers=["Date","Category","Payment Mode","Amount","Description"]
        elif kind=="category":
            rows=conn.execute("""SELECT c.category_name,COUNT(e.expense_id),ROUND(COALESCE(SUM(e.amount),0),2)
                FROM categories c LEFT JOIN expenses e ON e.category_id=c.category_id AND e.user_id=?
                GROUP BY c.category_id ORDER BY 3 DESC""",(uid,)).fetchall()
            headers=["Category","Transactions","Total"]
        else: return "Invalid export",400
    finally: conn.close()
    out=io.StringIO(); w=csv.writer(out); w.writerow(headers); w.writerows(rows)
    return Response(out.getvalue(),mimetype="text/csv",
                    headers={"Content-Disposition":f"attachment; filename={kind}_report.csv"})

@app.context_processor
def inject_user():
    return {"logged_in":"user_id" in session,"user_name":session.get("user_name")}

if __name__=="__main__":
    init_db(); seed_defaults()
    app.run(debug=False)
