from flask import Flask, render_template, request
from pymysql import connections
import os
import boto3
import logging

app = Flask(__name__)

DBHOST    = os.environ.get("DBHOST")    or "localhost"
DBUSER    = os.environ.get("DBUSER")    or "root"
DBPWD     = os.environ.get("DBPWD")     or "password"
DATABASE  = os.environ.get("DATABASE")  or "employees"
DBPORT    = int(os.environ.get("DBPORT", 3306))

STUDENT_NAME   = os.environ.get("STUDENT_NAME")  or "Student"
BG_IMAGE_URL   = os.environ.get("BG_IMAGE_URL")  or ""   # s3://bucket/image.jpg
BG_LOCAL_PATH  = "/app/static/bg.jpg"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_bg_image():
    if not BG_IMAGE_URL:
        logger.warning("BG_IMAGE_URL not set — no background image will be used.")
        return

    logger.info("Background image URL: %s", BG_IMAGE_URL)

    path = BG_IMAGE_URL.replace("s3://", "")
    bucket, key = path.split("/", 1)

    try:
        s3 = boto3.client("s3")
        os.makedirs(os.path.dirname(BG_LOCAL_PATH), exist_ok=True)
        s3.download_file(bucket, key, BG_LOCAL_PATH)
        logger.info("Background image downloaded to %s", BG_LOCAL_PATH)
    except Exception as e:
        logger.error("Failed to download background image: %s", e)


download_bg_image()

db_conn = connections.Connection(
    host=DBHOST,
    port=DBPORT,
    user=DBUSER,
    password=DBPWD,
    db=DATABASE,
)

table = "employee"


@app.route("/", methods=["GET", "POST"])
def home():
    return render_template("addemp.html", student_name=STUDENT_NAME)


@app.route("/about", methods=["GET", "POST"])
def about():
    return render_template("about.html", student_name=STUDENT_NAME)


@app.route("/addemp", methods=["POST"])
def AddEmp():
    emp_id        = request.form["emp_id"]
    first_name    = request.form["first_name"]
    last_name     = request.form["last_name"]
    primary_skill = request.form["primary_skill"]
    location      = request.form["location"]

    insert_sql = "INSERT INTO employee VALUES (%s, %s, %s, %s, %s)"
    cursor = db_conn.cursor()
    try:
        cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
        db_conn.commit()
        emp_name = f"{first_name} {last_name}"
    finally:
        cursor.close()

    return render_template("addempoutput.html", name=emp_name, student_name=STUDENT_NAME)


@app.route("/getemp", methods=["GET", "POST"])
def GetEmp():
    return render_template("getemp.html", student_name=STUDENT_NAME)


@app.route("/fetchdata", methods=["GET", "POST"])
def FetchData():
    emp_id = request.form["emp_id"]
    output = {}
    select_sql = (
        "SELECT emp_id, first_name, last_name, primary_skill, location "
        "FROM employee WHERE emp_id=%s"
    )
    cursor = db_conn.cursor()
    try:
        cursor.execute(select_sql, (emp_id,))
        result = cursor.fetchone()
        output["emp_id"]        = result[0]
        output["first_name"]    = result[1]
        output["last_name"]     = result[2]
        output["primary_skills"] = result[3]
        output["location"]      = result[4]
    except Exception as e:
        logger.error("DB fetch error: %s", e)
    finally:
        cursor.close()

    return render_template(
        "getempoutput.html",
        id=output["emp_id"],
        fname=output["first_name"],
        lname=output["last_name"],
        interest=output["primary_skills"],
        location=output["location"],
        student_name=STUDENT_NAME,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81, debug=True)
