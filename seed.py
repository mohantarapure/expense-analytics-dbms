
from database import init_db, get_connection
from werkzeug.security import generate_password_hash
from datetime import date, timedelta
import random

init_db()
conn=get_connection()
try:
    categories=["Food","Travel","Shopping","Bills","Education","Health","Entertainment","Other"]
    modes=["Cash","UPI","Credit Card","Debit Card","Bank Transfer"]
    for x in categories: conn.execute("INSERT OR IGNORE INTO categories(category_name) VALUES(?)",(x,))
    for x in modes: conn.execute("INSERT OR IGNORE INTO payment_modes(mode_name) VALUES(?)",(x,))
    users=[
        ("Demo User","demo@example.com",generate_password_hash("demo123")),
        ("Student User","student@example.com",generate_password_hash("student123"))
    ]
    for u in users: conn.execute("INSERT OR IGNORE INTO users(name,email,password) VALUES(?,?,?)",u)
    uid=conn.execute("SELECT user_id FROM users WHERE email='demo@example.com'").fetchone()[0]
    ids={r["category_name"]:r["category_id"] for r in conn.execute("SELECT * FROM categories")}
    mids={r["mode_name"]:r["payment_mode_id"] for r in conn.execute("SELECT * FROM payment_modes")}
    data=[
        ("Food",120,"Lunch","UPI"),("Travel",80,"Bus","Cash"),("Shopping",650,"Clothes","Credit Card"),
        ("Bills",1200,"Electricity","UPI"),("Education",500,"Books","Debit Card"),("Health",300,"Medicine","Cash"),
        ("Entertainment",250,"Movie","UPI"),("Food",180,"Dinner","UPI"),("Travel",120,"Auto","Cash"),
        ("Shopping",900,"Shoes","Credit Card"),("Bills",700,"Internet","UPI"),("Education",350,"Course","Debit Card"),
        ("Food",90,"Breakfast","Cash"),("Health",450,"Checkup","UPI"),("Entertainment",180,"Game","UPI"),
        ("Travel",200,"Train","Bank Transfer"),("Other",150,"Misc","Cash"),("Food",220,"Dinner","UPI"),
        ("Shopping",400,"Accessories","Credit Card"),("Bills",500,"Mobile","UPI"),
    ]
    existing=conn.execute("SELECT COUNT(*) FROM expenses WHERE user_id=?",(uid,)).fetchone()[0]
    if existing==0:
        today=date.today()
        for i,(cat,amt,desc,mode) in enumerate(data):
            dt=today-timedelta(days=i*4)
            conn.execute("""INSERT INTO expenses(user_id,category_id,payment_mode_id,amount,description,expense_date)
                VALUES(?,?,?,?,?,?)""",(uid,ids[cat],mids[mode],amt,desc,dt.isoformat()))
    month=date.today().strftime("%Y-%m")
    for cat,amt in [("Food",3000),("Travel",2000),("Shopping",3000),("Bills",2500),("Education",1500)]:
        conn.execute("""INSERT OR IGNORE INTO budgets(user_id,category_id,amount,month_year) VALUES(?,?,?,?)""",
                     (uid,ids[cat],amt,month))
    conn.commit()
finally:
    conn.close()
print("Database seeded. Demo: demo@example.com / demo123")
