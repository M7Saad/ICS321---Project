import psycopg2
from flask import Flask, g, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash


# --------------------- setup ---------------------#
def createapp():
    app = Flask(__name__, static_folder="static")
    app.secret_key = "allah y3een"
    return app


app = createapp()


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


##-----------Database!----------##


@app.route("/validate", methods=["POST"])
def validate():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM auth WHERE username = %s",
        (username,),
    )
    # if the user is not found or the password is incorrect return an error Message
    # else return the user role
    user = cur.fetchone()
    print(user)
    if user is None or not check_password_hash(user[2], password):
        return {"result": "Invalid username or password"}
    else:
        session["user_id"] = user[0]
        session["user_name"] = user[1]
        session["user_role"] = user[3]  ## either "Staff", "user"
        return {"result": user[3]}


@app.route("/addUser", methods=["POST"])
def addUser():
    """
    Adds a new user to the database
    data will include "name","address", "phone", "email", "DOB", "bloodtype", "weight", "password", type = (either "Donor" or "Recipient")
    + "disease" history which is in the format "disease1, disease2, ..."
    """
    data = request.get_json()
    # validate the bloodtype
    if data.get("bloodtype") not in ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]:
        return {"result": "Invalid bloodtype"}

    # validate the type
    if data.get("type") not in ["donor", "recipient"]:
        return {"result": "Invalid type"}

    # validate the weight
    if int(data.get("weight")) < 0 or int(data.get("weight")) > 200:
        return {"result": "Invalid weight"}

    # insert the data into the database
    db = get_db()
    cur = db.cursor()
    # generate id by counting the number of rows in the table
    cur.execute("SELECT MAX(id) FROM person")
    id = cur.fetchone()[0] + 1

    # insert the data into the person table
    cur.execute(
        "INSERT INTO person (id, name, address, phone, email, dob) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            id,
            data.get("name"),
            data.get("address"),
            data.get("phone"),
            data.get("email"),
            data.get("dob"),
        ),
    )
    # insert the data into the user table (id, bloodtype, weight)
    cur.execute(
        'INSERT INTO "user" VALUES (%s, %s, %s)',
        (id, data.get("bloodtype"), data.get("weight")),
    )

    # insert the data into the auth table (id, username, password, role)
    cur.execute(
        "INSERT INTO auth VALUES (%s, %s, %s, %s)",
        (
            id,
            data.get("email"),
            generate_password_hash(data.get("password")),
            data.get("type"),
        ),
    )

    # insert the data into the disease table
    if data.get("disease") != "":
        diseases = data.get("disease").split(",")
        for disease in diseases:
            cur.execute(
                "INSERT INTO disease_history VALUES (%s, %s)",
                (id, disease),
            )

    # if the user is a donor insert the data into the donor table
    if data.get("type") == "donor":
        cur.execute(
            "INSERT INTO donor VALUES (%s)",
            (id,),
        )
    else:
        # if the user is a recipient insert the data into the recipient table
        cur.execute(
            "INSERT INTO recipient VALUES (%s)",
            (id,),
        )
    print("done")
    return {"result": "success"}


@app.route("/searchID", methods=["POST"])
def searchID():
    """
    Searches for a user by id
    data will include "id"
    """
    data = request.get_json()
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT * FROM person WHERE id = %s",
        (data.get("id"),),
    )
    person = cur.fetchone()

    if person is None:
        return {"result": "Invalid ID"}
    # get type of user
    cur.execute(
        "SELECT role FROM auth WHERE id = %s",
        (data.get("id"),),
    )
    type = cur.fetchone()[0]
    # get the user
    cur.execute(
        'SELECT * FROM "user" WHERE id = %s',
        (data.get("id"),),
    )
    user = cur.fetchone()
    # get the diseases
    cur.execute(
        "SELECT * FROM disease_history WHERE id = %s",
        (data.get("id"),),
    )
    diseases = cur.fetchall()
    # convert the diseases to a string
    diseases_str = ""
    for disease in diseases:
        diseases_str += disease[1] + ", "
    if diseases_str != "":
        diseases_str = diseases_str[:-2]
    ##

    # keep the date of birth, without the time
    DOB = person[5].strftime("%Y-%m-%d")

    return {
        "result": {
            # from person
            "id": person[0],
            "name": person[1],
            "address": person[2],
            "phone": person[3],
            "email": person[4],
            "dob": DOB,
            # type
            "type": type,
            # from user
            "bloodtype": user[1],
            "weight": user[2],
            "disease": diseases_str,
        }
    }


@app.route("/remove", methods=["POST"])
def remove():
    """
    Removes a user from the database
    data will include "id"
    """
    tables = ["auth", "donor", "recipient", "disease_history", '"user"', "person"]
    data = request.get_json()
    db = get_db()
    cur = db.cursor()
    # remove from auth
    for table in tables:
        cur.execute(
            f"DELETE FROM {table} WHERE id = %s",
            (data.get("id"),),
        )
    return {"result": "success"}


@app.route("/getUsers", methods=["get"])
def getUsers():
    """
    Returns all users in the database (id, name, address, email, type, bloodtype, weight, disease)
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT ID FROM person",
    )
    users = cur.fetchall()
    ans = []
    # for each user get the type, bloodtype, weight, disease
    for i in range(len(users)):
        print(users[i][0], "!!!")
        ID = users[i][0]
        cur.execute(
            "SELECT * FROM person WHERE id = %s",
            (ID,),
        )
        person = cur.fetchone()

        # get type of user
        cur.execute(
            "SELECT role FROM auth WHERE id = %s",
            (ID,),
        )
        type = cur.fetchone()[0]
        # get the user
        cur.execute(
            'SELECT * FROM "user" WHERE id = %s',
            (ID,),
        )
        user = cur.fetchone()
        # get the diseases
        cur.execute(
            "SELECT * FROM disease_history WHERE id = %s",
            (ID,),
        )
        diseases = cur.fetchall()
        # convert the diseases to a string
        diseases_str = ""
        for disease in diseases:
            diseases_str += disease[1] + ", "
        if diseases_str != "":
            diseases_str = diseases_str[:-2]
        ##

        # keep the date of birth, without the time
        DOB = person[5].strftime("%Y-%m-%d")

        ans.append(
            {
                # from person
                "id": person[0],
                "name": person[1],
                "address": person[2],
                "email": person[4],
                # type
                "type": type,
                # from user
                "bloodtype": user[1],
                "weight": user[2],
                "disease": diseases_str,
            }
        )
    return {"result": ans}


# --------------------- html ---------------------#
@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(debug=True, port=6969)
