import psycopg2
import psycopg2.extras

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
        "SELECT * FROM auth WHERE email = %s",
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
    row = cur.fetchone()
    id = row[0] + 1 if row and row[0] is not None else 1

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


@app.route("/updateUser", methods=["POST"])
def updateUser():
    """
    Updates a user in the database
    data will include "id", "name","address", "email", "bloodtype", "weight", type = (either "Donor" or "Recipient"),
    "disease" history which is in the format "disease1, disease2, ..."
    """

    # update person
    data = request.get_json()
    data = data.get("row")
    print(data)
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE person SET address = %s, email = %s WHERE id = %s",
        (
            data.get("address"),
            data.get("email"),
            data.get("id"),
        ),
    )

    # update user
    cur.execute(
        'UPDATE "user" SET blood_type = %s, weight = %s WHERE id = %s',
        (data.get("bloodtype"), data.get("weight"), data.get("id")),
    )

    # update auth
    cur.execute(
        "UPDATE auth SET role = %s WHERE id = %s",
        (data.get("type"), data.get("id")),
    )

    # update disease
    # remove all diseases
    cur.execute(
        "DELETE FROM disease_history WHERE id = %s",
        (data.get("id"),),
    )
    # insert the new diseases
    print(data)
    if data.get("disease") != "":
        diseases = data.get("disease").split(",")
        for disease in diseases:
            cur.execute(
                "INSERT INTO disease_history VALUES (%s, %s)",
                (data.get("id"), disease),
            )

    return {"result": "success"}


@app.route("/adddrive", methods=["post"])
def addBloodDrive():
    """
    Adds a new blood drive to the database
    data will include "start_date", "end_date", "location"
    """
    data = request.get_json()
    db = get_db()
    cur = db.cursor()
    # generate id by counting the number of rows in the table
    cur.execute("SELECT MAX(event_id) FROM event")
    row = cur.fetchone()
    id = row[0] + 1 if row and row[0] is not None else 1
    pid = session["user_id"]
    # insert the data into the blood_drive table
    cur.execute(
        "INSERT INTO event VALUES (%s, %s, %s, %s, %s)",
        (data.get("stDate"), data.get("enDate"), data.get("loc"), id, pid),
    )
    return {"result": "success"}


@app.route("/getUserinfo", methods=["get"])
def getuserinfo():
    ID = session["user_id"]
    db = get_db()
    cur = db.cursor()
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

    return {
        # from person
        "id": person[0],
        "name": person[1],
        "address": person[2],
        "email": person[4],
        # type
        "type": type,
        # from user
        "weight": user[2],
        "disease": diseases_str,
    }


@app.route("/updateUserinfo", methods=["POST"])
def updateUserinfo():
    """
    Updates a user in the database
    data will include "id", "name","address", "email", "bloodtype", "weight", type = (either "Donor" or "Recipient"),
    "disease" history which is in the format "disease1, disease2, ..."
    """

    # update person
    data = request.get_json()
    data["id"] = session["user_id"]
    data = data.get("data")
    print(data)
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE person SET address = %s, email = %s WHERE id = %s",
        (
            data.get("address"),
            data.get("email"),
            data.get("id"),
        ),
    )

    # update user
    cur.execute(
        'UPDATE "user" SET weight = %s WHERE id = %s',
        (data.get("weight"), data.get("id")),
    )

    # update auth
    cur.execute(
        "UPDATE auth SET role = %s WHERE id = %s",
        (data.get("type"), data.get("id")),
    )

    # update disease
    # remove all diseases
    cur.execute(
        "DELETE FROM disease_history WHERE id = %s",
        (data.get("id"),),
    )
    # insert the new diseases
    print(data)
    if data.get("disease") != "":
        diseases = data.get("disease").split(",")
        for disease in diseases:
            cur.execute(
                "INSERT INTO disease_history VALUES (%s, %s)",
                (data.get("id"), disease),
            )

    return {"result": "success"}


@app.route("/getHistory", methods=["get"])
def getHistory():
    ID = session["user_id"]
    ROLE = session["user_role"]
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # if donor
    if ROLE == "donor":
        cur.execute(
            "SELECT * FROM DONATION WHERE donor_id = %s",
            (ID,),
        )
    else:
        # if recipient
        cur.execute(
            """SELECT bag.*, donation.* FROM bag 
 right JOIN donation ON bag.donation_id = donation.donation_id 
WHERE bag.pid = 4;""",
            (ID,),
        )
    events = cur.fetchall()

    ans = []
    for event in events:
        event = dict(event)
        event["Date"] = event["Date"].strftime("%Y-%m-%d")
        ans.append(event)

    # get
    return {"result": ans}


##########################################################################################
@app.route("/getReport", methods=["get"])
def getReport():
    # 1. List of all blood donations received in a week or a month.

    ID = session["user_id"]
    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """SELECT * 
        FROM bag 
        where bag.date_of_receving >= NOW() - INTERVAL '30 days'
        AND pid IS NOT NULL;""",
    )
    events = cur.fetchall()
    for event in events:
        event["date_of_receving"] = event["date_of_receving"].strftime("%Y-%m-%d")
        event["expire_date"] = event["expire_date"].strftime("%Y-%m-%d")
        event = dict(event)

    # get
    return {"result": events}


@app.route("/getReport2", methods=["get"])
def getBloodTypeReport():
    # query to get the total donations per event per blood type
    # select eventID,startDate, endDate, blood_type, sum(amount) from events, Donations, users
    # where events.eventID = Donations.eventID and Donations.donor_id = users.id
    # group by eventID, blood_type

    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """
        SELECT u.blood_type, SUM(d.units) as total_units
        FROM donation d
        JOIN "user" u ON d.donor_id = u.id
        GROUP BY u.blood_type;
        """
    )
    events = cur.fetchall()

    # get
    return {"result": events}


@app.route("/getReport3", methods=["get"])
def getreport3():
    # 1. List of all blood donations received in an event.

    db = get_db()
    cur = db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(
        """SELECT event.event_id, event.location, COALESCE(SUM(donation.units), 0) as total_donation
    FROM event
    LEFT JOIN donation ON event.event_id = donation.event_id
    GROUP BY event.event_id;""",
    )

    events = cur.fetchall()
    events = [dict(event) for event in events]
    # get
    return {"result": events}


@app.route("/getReport5", methods=["get"])
def getPaymentsReport():
    
    ID = session["user_id"]
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "select * from payments",
    )
    events = cur.fetchall()
    ans = []
    for event in events:
        ans.append(
            {
                "payment_id": event[0],
                "donor_id": event[1],
                "amount": event[2],
                "startDate": event[3].strftime("%Y-%m-%d"),
            }
        )
    # get
    return {"result": ans}


###################################################################################################
@app.route("/request", methods=["POST"])
def requestBlood():
    
    # Adds a new blood request to the database
    # data will include "bloodtype", "units"
    
    data = request.get_json()
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT MAX(request_id) FROM request")
    row = cur.fetchone()
    id = row[0] + 1 if row and row[0] is not None else 1
    pid = session["user_id"]
    cur.execute(
        "INSERT INTO request VALUES (%s, %s, %s, %s)",
        (id, data.get("bloodtype"), data.get("units"), pid),
    )
    return {"result": "success"}


# --------------------- html ---------------------#
@app.route("/", defaults={"path": "index.html"})
@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(debug=True, port=6969)
