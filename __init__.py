import psycopg2
from flask import Flask, g, request, session
from werkzeug.security import check_password_hash, generate_password_hash

# --------------------- setup ---------------------#
app = Flask(__name__)
app.secret_key = "allah y3een"


def get_db():
    """Opens a new database connection if there is none yet for the
    current application context."""
    if "db" not in g:
        g.db = psycopg2.connect(
            dbname="Blood Donation System",
            user="mohammed",
            password="123456",
            host="localhost",
            port="5432",
        )
        g.db.set_session(autocommit=True)
    return g.db


@app.teardown_appcontext
def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop("db", None)

    if db is not None:
        db.close()


##---------------------##


@app.route("/validate", methods=["POST"])
def validate():
    username = request.form.get("username")
    password = request.form.get("password")
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM auth WHERE username = %s",
        (username,),
    )
    # confirm the vlaue of the "Role" column if the user exists
    # if the user is not found, the value of the "Role" column will be None
    user = cur.fetchone()
    if user is None or not check_password_hash(user[2], password):
        return "False"
    else:
        session["user_id"] = user[0]
        session["user_name"] = user[1]
        session["user_role"] = user[3]
        return user[2]


# --------------------- html ---------------------#
@app.route("/")
def home():
    print("!@#$%^&*()")
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=6969)
