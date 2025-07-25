from flask import Flask, render_template, redirect, url_for , flash
import MySQLdb
import base64
from flask_weasyprint import HTML,render_pdf
import re
from flask_mail import Mail,Message
from Crypto.Cipher import AES
from passlib.hash import pbkdf2_sha256
from flask import request
import datetime
import time
from flask import session
import os
from customer_validation import RegistrationForm
from booking_validation import BookingForm
from login_validation import LoginForm
from reset_validation import ResetPasswordForm
from addAdmin_validation import AdminRegistrationForm
from addCar_validation import CarForm
from addDriver_validation import DriverForm
from feedback_validation import FeedbackForm
from payment_validation import CardPaymentForm, NetbankingForm
from crypto_utils import encrypt_answer, decrypt_answer
import hashlib

from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    current_user, login_required
)
from functools import wraps      # gives @wraps
from flask import abort          # used to send 403 Forbidden


app = Flask(__name__)

# ─── Flask‑Login bootstrap ───────────────────────────────────────────
login_manager = LoginManager()
login_manager.login_view = "signin"          # redirect target for @login_required
login_manager.session_protection = "strong"  # re‑auth if IP/UA changes
login_manager.init_app(app)

app.config.update(
    SESSION_COOKIE_SECURE=True,      # HTTPS‑only
    SESSION_COOKIE_HTTPONLY=True,    # JS cannot touch
    SESSION_COOKIE_SAMESITE="Lax",
    PERMANENT_SESSION_LIFETIME=datetime.timedelta(minutes=30)
)





app.config.update(
  DEBUG=True,
  MAIL_SERVER  = os.getenv("MAIL_SERVER", "mailhog"),
  MAIL_PORT    = int(os.getenv("MAIL_PORT", 1025)),
  MAIL_USE_TLS = False,
  MAIL_USE_SSL = False,
  MAIL_USERNAME= os.getenv("MAIL_USERNAME", ""),
  MAIL_PASSWORD= os.getenv("MAIL_PASSWORD", "")
)


#app.config.update(mail_settings)
mail = Mail(app)

app.secret_key = os.getenv("SECRET_KEY")

conn = MySQLdb.connect(
    host=os.getenv("DB_HOST", "db"),
    user=os.getenv("DB_USER", "root"),
    passwd=os.getenv("DB_PASSWORD", "root"),
    db=os.getenv("DB_NAME", "car_rental")
)
cursor = conn.cursor()
master_password = os.getenv("MASTER_PASSWORD", "")
payment_type = ""
payment_status = ["Paid", "Not Paid"]

def checkstring(inputstring):
    return not any(char.isalpha() for char in inputstring)


class User(UserMixin):
    """
    Wrapper around a row in Cust_User or Admin_User.

    `id` is required by Flask‑Login → here: primary‑key/userId varchar.
    """
    def __init__(self, record: dict, role: str):
        self.id       = record["userId"]            # unique identifier
        self.fname    = record.get("fName")
        self.lname    = record.get("lName")
        self.role     = role                        # "Customer" / "Admin"

    # convenience used in templates or @roles_required decorator
    def is_admin(self):
        return self.role == "Admin"

@login_manager.user_loader
def load_user(user_id: str):
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    # try customer first
    cur.execute("SELECT * FROM Cust_User WHERE userId = %s", (user_id,))
    row = cur.fetchone()
    if row:
        return User(row, "Customer")

    cur.execute("SELECT * FROM Admin_User WHERE userId = %s", (user_id,))
    row = cur.fetchone()
    if row:
        return User(row, "Admin")

    return None


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)            # HTTP “Forbidden”
            return fn(*args, **kwargs)
        return wrapped
    return decorator

	
#-----------------------------------------------FRONT PAGE -------------------------------------------------------
@app.route("/",methods=['GET','POST'])
def homepage():
	return render_template("index.html")
#---------------------------ADD New CUSTOMER ----------------------------------------------------------------------------

@app.route('/addcustomer/', methods=['GET','POST'])
def register():
    return render_template('addcustomer.html')
	

@app.route('/adduser/', methods=['POST'])
def adduser():
    """Handle customer registration (POST from addcustomer.html)."""

    # ------------------------------------------------------------------  
    # 1) Validate & normalise the incoming form data -------------------
    # ------------------------------------------------------------------
    form = RegistrationForm(request.form)
    if not form.is_valid():
        # Push every validation error into the flashing system and
        # round-trip the user straight back to the form.
        for msg in form.errors:
            flash(msg, category="error")
        return render_template("addcustomer.html"), 400  # Bad Request

    data = form.cleaned_data        # safe, canonicalised values
    #   data = {
    #       'FName': 'Alice', 'lName': 'Smith', 'username': 'asmith',
    #       'email': 'alice@example.com', 'phone': '0123456789',
    #       'age': 25, 'password': 'S3cur3!!', 'squestion': 2,
    #       'answer': 'Greenwood'
    #   }

    # ------------------------------------------------------------------  
    # 2) Business rules that depend on DB state ------------------------
    # ------------------------------------------------------------------
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Cust_User WHERE userId = %s", (data["username"],))
    if cursor.fetchone():
        flash("Sorry, that username is already taken.", category="error")
        return render_template("addcustomer.html"), 409  # Conflict

    # ------------------------------------------------------------------  
    # 3) Persist the new user ------------------------------------------
    # ------------------------------------------------------------------
    hash_password = pbkdf2_sha256.hash(data["password"])

    # AES-encrypt the security answer exactly as before
    cipher = AES.new(b"1234567890123456", AES.MODE_ECB)
    padded = data["answer"].rjust(32).encode("utf-8")
    enc_ans = base64.b64encode(cipher.encrypt(padded)).decode("utf-8")

    current_date = datetime.datetime.now().strftime("%d-%m-%Y")

    cursor.execute(
        """
        INSERT INTO Cust_User
            (userId, fName, lName, emailId, phone,
             registration_Date, password, reset_Question, reset_Ans_Type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data["username"], data["FName"], data["lName"], data["email"],
            data["phone"], current_date, hash_password,
            str(data["squestion"]), enc_ans,
        ),
    )
    conn.commit()

    # ------------------------------------------------------------------  
    # 4) Side-effects (welcome email) ----------------------------------
    # ------------------------------------------------------------------
    msg = Message(
        "Welcome to Car Rental Services",
        sender="Car Rental Services",
        recipients=[data["email"]],
    )
    msg.body = (
        "Thank you for signing up with Car Rental Service.\n"
        "You can now book a cab whenever you need!"
    )
    mail.send(msg)

    flash("Successfully registered — please sign in.", category="success")
    return redirect(url_for("signin"))
			
			
			
#---------------------------------------END------------------------------------------------------

#-------------------------------------LOGIN PAGE--------------------------------------------------------
@app.route('/login')

def signin():
	print("entered")
	return render_template('signin.html')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You’ve been logged out.", "info")
    return redirect(url_for("signin"))
	
	
@app.route("/echo", methods=["POST"])
def sign():
    """
    POST target of signin.html – authenticates and starts session.
    """
    form = LoginForm(request.form)
    if not form.is_valid():
        for err in form.errors:
            flash(err, "error")
        return render_template("signin.html"), 400

    username = form.cleaned_data["username"]
    password = form.cleaned_data["password"]

    cur = conn.cursor(MySQLdb.cursors.DictCursor)

    # unified lookup
    cur.execute("""
        SELECT * , 'Customer' AS role FROM Cust_User WHERE userId = %s
        UNION ALL
        SELECT * , 'Admin'    AS role FROM Admin_User WHERE userId = %s
        """, (username, username))
    record = cur.fetchone()

    if not record or not pbkdf2_sha256.verify(password, record["password"]):
        flash("Invalid username or password.", "error")
        return render_template("signin.html"), 401

    user = User(record, record["role"])
    login_user(user, remember=False)        # remember=False → 30‑min absolute lifetime
    flash("Logged in successfully!", "success")

    # audit trail
    now = datetime.datetime.now()
    cur.execute("""
        INSERT INTO Login_History (user, userId, Date, Time)
        VALUES (%s, %s, %s, %s)""",
        (user.role, user.id, now.strftime("%d-%m-%Y"), now.strftime("%H:%M:%S")))
    conn.commit()

    # role‑based landing page
    return (
        redirect(url_for("adminpage"))
        if user.is_admin()
        else redirect(url_for("bookingdriver"))
    )


#**********************************RESET PASSWORD-----------------------------------------------------------------------------------

@app.route('/resetpassword/',methods=['GET','POST'])

def resetdriver():
	print("Entered")
	return render_template("resetpassword.html")

@app.route("/reset/", methods=["POST"])
def resetpasswordform():
    """Handle resetpassword.html POST."""
    # ── 1. Validate form ───────────────────────────────────────────────
    form = ResetPasswordForm(request.form)
    if not form.is_valid():
        for e in form.errors:
            flash(e, "error")
        return render_template("resetpassword.html"), 400

    data       = form.cleaned_data
    username   = data["username"]
    squestion  = data["squestion"]          # int (1-4)
    answer_in  = data["answer"]
    new_plain  = data["password"]

    cursor = conn.cursor()

    # ── 2. Locate user (customer -or- admin) ──────────────────────────
    cursor.execute(
        "SELECT reset_Question, reset_Ans_Type FROM Cust_User WHERE userId = %s",
        (username,),
    )
    row   = cursor.fetchone()
    table = "Cust_User"

    if not row:
        cursor.execute(
            "SELECT reset_Question, reset_Ans_Type FROM Admin_User WHERE userId = %s",
            (username,),
        )
        row   = cursor.fetchone()
        table = "Admin_User"

    if not row:
        flash("Entered username does not exist.", "error")
        return render_template("resetpassword.html"), 404

    stored_question, enc_answer_b64 = row

    # ── 3. Check selected security question ───────────────────────────
    if int(stored_question) != squestion:
        flash("Selected security question does not match our records.", "error")
        return render_template("resetpassword.html"), 401

    # ── 4. Decrypt & verify answer (CBC, random IV) ───────────────────
    stored_answer = decrypt_answer(enc_answer_b64)
    if stored_answer != answer_in:
        flash("Security answer incorrect.", "error")
        return render_template("resetpassword.html"), 401

    # ── 5. Update password ────────────────────────────────────────────
    new_hash = pbkdf2_sha256.hash(new_plain)
    cursor.execute(
        f"UPDATE {table} SET password = %s WHERE userId = %s",
        (new_hash, username),
    )
    conn.commit()

    flash("Password successfully changed — please log in.", "success")
    return render_template("signin.html")

#--------------------------------------------BOOKING PAGE-----------------------------------------------------

@app.route('/booking/',methods = ['GET','POST'])
@login_required
def bookingdriver():
	
	print("entered")
	#booking()
	return render_template('booking.html')
	
	
@app.route('/bookingNow/', methods=['POST'])
@login_required
def booking():
    # ------------------------------------------------------------------  
    # 1) Validate form --------------------------------------------------
    # ------------------------------------------------------------------
    form = BookingForm(request.form)
    if not form.is_valid():
        for e in form.errors:
            flash(e, category="error")
        return render_template("booking.html"), 400

    data = form.cleaned_data     # safe, canonicalised values
    # data example:
    # { userId: 'alice', cab: 1, startDate: '2025-07-15',
    #   endDate: '2025-07-16', time: '09:00', route: 2,
    #   pickupLocation: 'College Road', dropoffLocation: 'Nagpur Station' }

    # ------------------------------------------------------------------  
    # 2) Business checks (must hit DB) ---------------------------------
    # ------------------------------------------------------------------
    cursor = conn.cursor()

    # Confirm user exists
    cursor.execute("SELECT 1 FROM Cust_User WHERE userId = %s", (data["userId"],))
    if not cursor.fetchone():
        flash("Entered username does not exist.", category="error")
        return render_template("booking.html"), 404

    # Fetch customer meta
    cursor.execute(
        "SELECT fName, lName, emailId, phone FROM Cust_User WHERE userId = %s",
        (data["userId"],),
    )
    fname, lname, email, phone = cursor.fetchone()

    # Figure out cab name from index
    CAB_LIST = ["Hatchback", "Sedan", "SUV"]
    cab_name = CAB_LIST[data["cab"]]

    # Validate car & driver availability
    cursor.execute(
        "SELECT Car_id FROM Car WHERE status = 'Available' AND Car_type = %s LIMIT 1",
        (cab_name,),
    )
    car_row = cursor.fetchone()
    if not car_row:
        return redirect(url_for("allbooked"))  # shows *Sorry, all cars booked* page
    carid = car_row[0]

    cursor.execute("SELECT driverId FROM Driver WHERE status = 'Available' LIMIT 1")
    drv_row = cursor.fetchone()
    if not drv_row:
        return redirect(url_for("allbooked"))
    driverid = drv_row[0]

    # ------------------------------------------------------------------  
    # 3) Persist booking; lock car/driver -------------------------------
    # ------------------------------------------------------------------
    cursor.execute("UPDATE Car    SET status='BOOKED' WHERE Car_id   = %s", (carid,))
    cursor.execute("UPDATE Driver SET status='BOOKED' WHERE driverId = %s", (driverid,))

    cab_routes = ['Nashik-Pune', 'Nashik-Mumbai', 'Nashik-Nagpur',
                  'Nashik-Dhule', 'Nashik-Aurangabad']
    route_name = cab_routes[data["route"]]

    cursor.execute(
        """
        INSERT INTO Booking
            (userId, Cab, startDate, endDate, Pickup_time,
             Pickup_location, Drop_off_location, driverId, carid, cab_route)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data["userId"], cab_name, data["startDate"], data["endDate"],
            data["time"], data["pickupLocation"], data["dropoffLocation"],
            driverid, carid, route_name,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid

    # store
    session["custid"]      = data["userId"]
    session["driverid"]    = driverid
    session["carid"]       = carid
    session["booking_id"]  = new_id
    # read
    custid     = session.get("custid")
    driverID   = session.get("driverid")
    CARID      = session.get("carid")
    b_actual_id = session.get("booking_id")

    cursor.execute(
        "SELECT bookingId FROM Booking WHERE driverId=%s AND carid=%s "
        "ORDER BY bookingId DESC LIMIT 1",
        (driverid, carid),
    )
    b_actual_id = cursor.fetchone()[0]

    flash("Booking created — proceed to payment.", category="success")
    return redirect(url_for("paymentdriver"))
#--------------------------------------------------BOOKING PAGE ENDS------------------------------------------------------------------------------

#------------------------------------------------DISPLAY BOOKING ------------------------------------------------------------------

@app.route("/displaybooking/",methods=['GET','POST'])
def displaybooking():
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM Booking""")
	data5 = cursor.fetchall()
	cursor.close()
	
	return render_template("displaybooking.html",data = data5)
	
#--------------------------------------------DISPLAY BOOKING END--------------------------------------------------------------------
#--------------------------------------------ADMIN PAGE -------------------------------------------------------------
@app.route('/adminpage/',methods=['GET','POST'])
@roles_required("Admin")
def adminpage():
	print("Entered") 	#Testing
	
	return render_template("adminpage.html")
#---------------------------------END ADMIN PAGE-----------------------------------------------

#----------------------------------LOGIN HISTORY----------------------------------------------
@app.route("/logindetails/",methods=['GET','POST'])
@roles_required("Admin")
def logindetails():
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM Login_History""")
	data5 = cursor.fetchall()
	cursor.close()
	
	return render_template("loginhistory.html",data = data5)
#------------------------------------FEEDBACK FORM------------------------------------------------------------

@app.route('/feedback/',methods=['GET','POST'])
def feedbackdriver():
	print("Entered") 	#Testing
	
	return render_template("feedback.html")
	

@app.route('/addfeedback/',methods=['GET','POST'])

def feedbackform():
    """Persist customer feedback (POST from feedback.html)."""
    form = FeedbackForm(request.form)
    if not form.is_valid():
        for err in form.errors:
            flash(err, category="error")
        return render_template("feedback.html"), 400

    data = form.cleaned_data
    ratings_lookup = ["Excellent", "Good", "Neutral", "Poor"]
    user_rating = ratings_lookup[data["rating"]]

    cursor = conn.cursor()

    # Verify user exists (customer only)
    cursor.execute("SELECT fName, lName FROM Cust_User WHERE userId = %s", (data["userid"],))
    row = cursor.fetchone()
    if not row:
        flash("User ID not found. Please register first.", category="error")
        return render_template("feedback.html"), 404

    fname, lname = row

    today = datetime.datetime.now().strftime("%d-%m-%Y")

    cursor.execute(
        """
        INSERT INTO Feedback
            (userId, fName, lName, emailId, rating, comments, Date)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data["userid"],
            fname,
            lname,
            data["email"],
            user_rating,
            data["comments"],
            today,
        ),
    )
    conn.commit()

    flash("Feedback successfully sent!", category="success")
    return render_template("feedback.html")
#---------------------------------------------------FEEDBACK FORM END-------------------------------------------------------------------
#-------------------------------------------------ADD ADMIN-------------------------------------------------------------------------------------
@app.route('/addadmin/', methods=['GET','POST'])
@roles_required("Admin")
def addadmindriver():
    return render_template('addadmin.html')

@app.route("/addADMIN/", methods=["POST"])
@roles_required("Admin")
def addadmin():
    """Create a new admin account (POST from addadmin.html)."""
    form = AdminRegistrationForm(request.form)
    if not form.is_valid():
        for err in form.errors:
            flash(err, category="error")
        return render_template("addadmin.html"), 400

    data = form.cleaned_data
    cursor = conn.cursor()

    # ── 1. Uniqueness check ───────────────────────────────────────────
    cursor.execute("SELECT 1 FROM Admin_User WHERE userId = %s", (data["username"],))
    if cursor.fetchone():
        flash("Sorry, that username is already present.", "error")
        return render_template("addadmin.html"), 409

    # ── 2. Hash + encrypt sensitive fields ────────────────────────────
    hash_password = pbkdf2_sha256.hash(data["password"])
    enc_ans       = encrypt_answer(data["answer"])      # CBC, random IV

    today = datetime.datetime.now().strftime("%d-%m-%Y")

    # ── 3. Persist ────────────────────────────────────────────────────
    cursor.execute(
        """
        INSERT INTO Admin_User
            (userId, fName, lName, emailId, phone,
             registration_Date, password, reset_Question, reset_Ans_Type)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            data["username"], data["FName"], data["lName"],
            data["email"], data["phone"], today,
            hash_password, str(data["squestion"]), enc_ans,
        ),
    )
    conn.commit()

    flash("Admin successfully registered!", "success")
    return render_template("addadmin.html")
			

#-----------------------------------------------DISPLAY ADMIN DETAILS-------------------------------------------------------------------------------
@app.route("/admindetails/",methods=['GET','POST'])
@roles_required("Admin")
def admindetails():
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM Admin_User""")
	data = cursor.fetchall()
	cursor.close()
	
	return render_template("admindetails.html",data = data)
#------------------------------------------------DISPLAY ADMIN ENDS--------------------------------------------------------------------------

#------------------------------------------------DELETE ADMIN---------------------------------------------------------------------------------------
@app.route("/deleteadmin/",methods=['GET','POST'])
@roles_required("Admin")
def deleteadmindriver():
	return render_template("deleteadmin.html")	
	
@app.route("/deleteADMIN/",methods=['GET','POST'])
@roles_required("Admin")
def deleteadmin():
	cursor = conn.cursor()
	mpassword = request.form["mpassword"]
	dusername = str(request.form["dusername"])
	husername = request.form["husername"]
	adflag = False
	cursor.execute("""SELECT userId FROM Admin_User""")
	usernamesad = cursor.fetchall()
	usernames_listad = list(usernamesad)
	usernames_lenad = len(usernames_listad)
	for a in range(0,usernames_lenad):
		if usernames_listad[a][0] == dusername:
			adflag = True
	if adflag == False:
		flash("Entered Username does not Exist !!!")
		return render_template("deleteadmin.html")
		
	if master_password == mpassword:
		cursor.execute("""DELETE FROM Admin_User WHERE userId = %s""",[dusername])
		conn.commit()
		print(mpassword,dusername,husername)
		flash("Admin Successfully Deleted !!!")
		return render_template("deleteadmin.html")
	else:
		flash("Incorrect Master Password !!!")
		return render_template("deleteadmin.html")
		
		
#------------------------------------------END DELETE ADMIN ----------------------------------------------------------------------
#----------------------------------------FEEDBACK DISPLAY-----------------------------------------------------------------------

@app.route("/feedbackdisplay/",methods=['GET','POST'])

def feedbackdisplay():
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM Feedback""")
	data1 = cursor.fetchall()
	cursor.close()
	
	return render_template("feedbackdisplay.html",data = data1)
	
#------------------------------------FEEDBACK DISPLAY END -------------------------------------------------------------------------------
#-----------------------------------Display Customer Details----------------------------
@app.route("/displaycustomer/",methods=['GET','POST'])

def displaycustomer():
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM Cust_User""")
	data1 = cursor.fetchall()
	cursor.close()
	
	return render_template("displaycustomers.html",data = data1)
#-------------------------------------DELETE CUSTOMER USER-----------------------------------------------------------------------------
@app.route("/deleteuser/",methods=['GET','POST'])

def deleteuserdriver():
	return render_template("deleteuser.html")	
	
@app.route("/deleteUSER/",methods=['GET','POST'])

def deleteuser():
	cursor = conn.cursor()
	dusername1 = str(request.form["dusername"])
	husername1 = request.form["husername"]
	
	udflag = False
	cursor.execute("""SELECT userId FROM Cust_User""")
	usernamesud = cursor.fetchall()
	usernames_listud = list(usernamesud)
	usernames_lenud = len(usernames_listud)
	for a in range(0,usernames_lenud):
		if usernames_listud[a][0] == dusername1:
			udflag = True
	if udflag == False:
		flash("Entered Username does not Exist !!!")
		return render_template("deleteuser.html")
		
	cursor.execute("""DELETE FROM Cust_User WHERE userId = %s""",[dusername1])
	conn.commit()
	#print(mpassword,dusername,husername)
	cursor.close()
	flash("Customer Successfully Deleted !!!")
	return render_template("deleteuser.html")
	
#------------------------------DELETE CUSTOMER ENDS --------------------------------------------------------------------------------

#----------------------------------ADD NEW CAR -----------------------------------------------------------------------------------------------

@app.route("/addcar/",methods=['GET','POST'])

def addcardriver():
	return render_template("addcar.html")

@app.route("/addCAR/", methods=["POST"])
def addcarform():
    """Add a new vehicle to inventory (POST from addcar.html)."""
    form = CarForm(request.form)
    if not form.is_valid():
        for e in form.errors:
            flash(e, category="error")
        return render_template("addcar.html"), 400

    data = form.cleaned_data
    car_types = ["Sedan", "Hatchback", "SUV"]
    car_type_name = car_types[data["type"]]

    cursor = conn.cursor()

    # Business-level uniqueness checks
    cursor.execute(
        "SELECT 1 FROM Car WHERE Car_id = %s OR registeration_no = %s",
        (data["carid"], data["registration"]),
    )
    if cursor.fetchone():
        flash("Car ID or registration number already exists.", category="error")
        return render_template("addcar.html"), 409

    cursor.execute(
        """
        INSERT INTO Car
            (Car_id, model_name, registeration_no,
             seating_capacity, Car_type, price_per_km)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            data["carid"],
            data["model"],
            data["registration"],
            data["seating"],
            car_type_name,
            data["price"],
        ),
    )
    conn.commit()

    flash("New car successfully added!", category="success")
    return render_template("addcar.html")

	
#-----------------------------------ADD CAR ENDS---------------------------------------------------------------------------------

#------------------------------------------------DISPLAY CARS-----------------------------------------------------------------------------

@app.route("/displaycars/",methods=['GET','POST'])

def displaycars():
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM Car""")
	data2 = cursor.fetchall()
	cursor.close()
	
	return render_template("displaycars.html",data = data2)
#--------------------------------------------DISPLAY CAR ENDS-------------------------------------------------------------------------------

#---------------------------------------------DELETE CAR----------------------------------------------------------------------------------

@app.route("/deletecars/",methods=['GET','POST'])

def deletecardriver():
	return render_template("deletecars.html")	
	
@app.route("/deleteCARS/",methods=['GET','POST'])

def deletecar():
	cursor = conn.cursor()
	carid = str(request.form["carid"])
	
	cflag = False
	cursor.execute("""SELECT Car_id FROM Car""")
	carids = cursor.fetchall()
	carid_list = list(carids)
	carid_list_len = len(carid_list)
	for a in range(0,carid_list_len):
		if carid_list[a][0] == carid:
			cflag = True
	if cflag == False:
		flash("Entered CarId does not Exist !!!")
		return render_template("deletecars.html")
		
	cursor.execute("""DELETE FROM Car WHERE Car_id = %s""",[carid])
	conn.commit()
	#print(mpassword,dusername,husername)
	cursor.close()
	flash("Car Successfully Deleted !!!")
	return render_template("deletecars.html")
	

#-----------------------------------------------------------------------

#---------------------------------------------ADD Driver-----------------------------------------------------------------------------------------

@app.route("/adddriver/",methods=['GET','POST'])

def adddriver():
	return render_template("adddriver.html")

@app.route("/addDRIVER/", methods=["POST"])
def adddriverform():
    """Add a new driver (POST from adddriver.html)."""
    form = DriverForm(request.form)
    if not form.is_valid():
        for err in form.errors:
            flash(err, category="error")
        return render_template("adddriver.html"), 400

    data = form.cleaned_data
    cursor = conn.cursor()

    # Ensure license number is unique
    cursor.execute("SELECT 1 FROM Driver WHERE licence_no = %s", (data["license"],))
    if cursor.fetchone():
        flash("License number already exists.", category="error")
        return render_template("adddriver.html"), 409

    cursor.execute(
        """
        INSERT INTO Driver (fName, lName, phone_no, licence_no, age)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            data["dfname"],
            data["dlname"],
            data["dphone"],
            data["license"],
            data["dage"],
        ),
    )
    conn.commit()
    flash("New driver successfully added!", category="success")
    return render_template("adddriver.html")

	
#-------------------------------------ADD DRIVER END------------------------------------------------

#-------------------------------Display Driver -------------------------------------------------
@app.route("/displaydrivers/",methods=['GET','POST'])

def displaydriver():
	cursor = conn.cursor()
	cursor.execute("""SELECT * FROM Driver""")
	data1 = cursor.fetchall()
	cursor.close()
	
	return render_template("displaydrivers.html",data = data1)
	
#----------------------------DISPLAY DRIVER ENDS------------------------------------------------------------

#---------------------------DELETE DRIVER-----------------------------------------------------------------
@app.route("/deletedriver/",methods=['GET','POST'])

def delete_driver():
	return render_template("deletedriver.html")	
	
@app.route("/deleteDriver/",methods=['GET','POST'])

def deletedriver():
	cursor = conn.cursor()
	driverid = str(request.form["driverid"])
	
	'''dflag = False
	cursor.execute("""SELECT driverId FROM Driver""")
	driverids = cursor.fetchall()
	driverid_list = list(driverids)
	driverid_list_len = len(driverid_list)
	for a in range(0,driverid_list_len):
		if driverid_list[a][0] == driverid:
			dflag = True
	if dflag == False:
		flash("Entered DriverId does not Exist !!!")
		return render_template("deletedriver.html")
	'''
	cursor.execute("""DELETE FROM Booking WHERE driverId = %s""",[driverid])	
	cursor.execute("""DELETE FROM Driver WHERE driverId = %s""",[driverid])
	conn.commit()
	#print(mpassword,dusername,husername)
	cursor.close()
	flash("Driver Successfully Deleted !!!")
	return render_template("deletedriver.html")

#----------------------------ABOUT PAGE-------------------------------------------

@app.route('/aboutpage/',methods=['GET','POST'])

def aboutpage():
	print("Entered") 	#Testing
	
	return render_template("about.html")	
	
@app.route('/contactpage/',methods=['GET','POST'])

#--------------------------END ABOUT PAGE -------------------------------------------------------------------------

@app.route("/payment",methods=["GET","POST"])
@login_required
def paymentdriver():
	print("ENTERED")
	
	return render_template("payment.html")
	
# ─── shared helper ──────────────────────────────────────────────────────────
def _process_payment(payment_type: str, *, status: str):
    """
    Persist a Payment row for the *current* customer/booking context.

    Returns a redirect() response to /generateinvoice (or back to /payment on error).
    """
    km_map = {
        "Nashik-Pune": 211,
        "Nashik-Mumbai": 165,
        "Nashik-Nagpur": 680,
        "Nashik-Dhule": 144,
        "Nashik-Aurangabad": 160,
    }

    cursor = conn.cursor()

    # Find the latest booking for the user / car / driver trio.
    cursor.execute(
        """
        SELECT bookingId, cab_route, carid
          FROM Booking
         WHERE userId = %s AND carid = %s AND driverId = %s
      ORDER BY bookingId DESC
         LIMIT 1
        """,
        (custid, CARID, driverID),
    )
    row = cursor.fetchone()
    if not row:
        flash("Booking context lost – please start over.", "error")
        return render_template("payment.html"), 404

    booking_id, cab_route, carid = row
    km = km_map[cab_route]

    cursor.execute("SELECT price_per_km FROM Car WHERE Car_id = %s", (carid,))
    price_per_km = int(cursor.fetchone()[0])
    total_amount = km * price_per_km

    cursor.execute(
        "INSERT INTO Payment (payment_type, status, bookingId, total_amount) "
        "VALUES (%s, %s, %s, %s)",
        (payment_type, status, booking_id, total_amount),
    )
    conn.commit()

    flash("Payment recorded.", "success")
    return redirect(url_for("invoice"))  # existing route “/generateinvoice/”


# ─── CREDIT CARD ────────────────────────────────────────────────────────────
@app.route("/creditPAYMENT", methods=["POST"])
@login_required
def credit_payment():
    form = CardPaymentForm(request.form)
    if not form.is_valid():
        for msg in form.errors:
            flash(msg, "error")
        return render_template("payment.html"), 400

    return _process_payment("Credit Card", status="Paid")


# ─── NET BANKING ────────────────────────────────────────────────────────────
@app.route("/netbankingPAYMENT", methods=["POST"])
@login_required
def netbanking_payment():
    form = NetbankingForm(request.form)
    if not form.is_valid():
        for msg in form.errors:
            flash(msg, "error")
        return render_template("payment.html"), 400

    status = "Paid" if form.cleaned_data["radio"] == "0" else "Not Paid"
    return _process_payment("Net Banking", status=status)


# ─── DEBIT CARD ─────────────────────────────────────────────────────────────
@app.route("/debitPAYMENT", methods=["POST"])
@login_required
def debit_payment():
    form = CardPaymentForm(request.form)
    if not form.is_valid():
        for msg in form.errors:
            flash(msg, "error")
        return render_template("payment.html"), 400

    return _process_payment("Debit Card", status="Paid")

#------------------------PAYMENT END--------------------------------------------
#-----------------------INVOICE ------------------------------------------------------------------

@app.route("/generateinvoice/",methods=['GET','POST'])
@login_required
def invoice():
	cursor = conn.cursor()
	
	print("CUSTID : ",custid)
	#user_id=request.form['user']
	cursor.execute("""SELECT carId FROM Booking WHERE bookingId = %s""",[b_actual_id])
	carr = cursor.fetchall()
	carrid = carr[0][0]
	#print(bookingid)
	
	cursor.execute("""SELECT model_name FROM Car WHERE car_id = %s""",[carrid])
	modell = cursor.fetchall()
	model = modell[0][0]
	#print(bookingId)
	#cursor.execute("""select Payment_id from Payment where status=%s and payment_type=%s""",(payment,payment_type))
	#pay=cursor.fetchall()
	#payment_id=pay[0][0]
	cursor.execute("""SELECT fName,lName FROM Cust_User where userId=%s""",[custid])
	#data5 = cursor.fetchall()
	data5 = cursor.fetchall()
	cursor.execute("""SELECT emailId FROM Cust_User WHERE userId = %s""",[custid])
	emaill = cursor.fetchall()
	semail = emaill[0][0]
	print(data5)
	data10=data5[0][0] +" "+data5[0][1]
	cursor.execute("""SELECT phone FROM Cust_User where userId=%s""",[custid])
	p_no=cursor.fetchall()
	p_no1=p_no[0][0]
	print(p_no)
	cursor.execute("""SELECT Cab,startdate,endDate,Pickup_time,Pickup_location,Drop_off_location FROM Booking where bookingId=%s""",[b_actual_id])
	union=cursor.fetchall()
	Cab=union[0][0]
	Sd=union[0][1]
	Ed=union[0][2]
	P_time=union[0][3]
	P_loc=union[0][4]
	D_loc=union[0][5]
	cursor.execute("""SELECT driverId FROM Booking where  bookingId=%s""",[b_actual_id])
	d_id=cursor.fetchall()
	driverid=d_id[0][0]
	cursor.execute("""SELECT fName,lName FROM Driver where driverId=%s""",[driverid])
	d_name=cursor.fetchall()
	d_full_name=d_name[0][0]+" "+d_name[0][1]
	cursor.execute("""SELECT phone_no FROM Driver where driverId=%s""",[driverid])
	dphone = cursor.fetchall()
	dphoneno = dphone[0][0]
	cursor.execute("""SELECT payment_type  FROM Payment where bookingId=%s""",[b_actual_id])
	pType=cursor.fetchall()
	print("PTYPE",pType)
	P_type=pType[0][0]
	
	cursor.execute("""SELECT total_amount FROM Payment where bookingId=%s""",[b_actual_id])
	amt1=cursor.fetchall()
	amt=amt1[0][0]
	bID = str(b_actual_id)
	msg=Message("Your Cab is Successfully Booked !!!",sender="Car Rentel Services",recipients=[semail])
	msg.body = "Thank you for Booking Cab from Us.Your Booking ID is "+bID
	mail.send(msg)
			
	return render_template("invoice.html",data =b_actual_id,name=data10,cab=Cab,cab_model=model,sd=Sd,ed=Ed,p_time=P_time,p_loc=P_loc,d_loc=D_loc,dName=d_full_name,dphone1=dphoneno,p_type=P_type,amount = amt)
	
	
#---------------------DISPLAY CAR STATUS ---------------------------------------

@app.route("/displaycarstatus/",methods=['GET','POST'])

def carstatusdriver():
	cursor = conn.cursor()
	cursor.execute("""SELECT Car_id,model_name,registeration_no,Car_type,status FROM Car""")
	data1 = cursor.fetchall()
	cursor.close()
	
	return render_template("displaystatuscar.html",data = data1)

#---------------------DISPLAY CAR STATUS ENDS---------------------------------------.

#---------------------Change CAR STATUS ---------------------------------------
@app.route("/changecarstatus/",methods=['GET','POST'])

def changecarstatusdriver():
	return render_template("changecarstatus.html")

@app.route("/changecarSTATUS/",methods=['GET','POST'])

def changecarstatus():
	ccflag = False
	status_type = ['Available','Booked']
	Car_Type = ""
	cursor = conn.cursor()
	carid1 = request.form["cari"]
	
	cursor.execute("""SELECT Car_id FROM Car WHERE Car_id = %s""",[carid1])
	cid = cursor.fetchall()
	cid_list = list(cid)
	cid_len = len(cid_list)
	for a in range(0,cid_len):
		if cid_list[a][0] == carid1:
			ccflag = True
	if ccflag == False:
		flash("Entered CarID is Invalid !!!")
		return render_template("changecarstatus.html")
			
	Type = int(request.form["status"])
	status_Type = status_type[Type]
	
	cursor.execute("""UPDATE Car SET status = %s WHERE Car_id = %s""",(status_Type,carid1))
	conn.commit()
	cursor.close()
	#print(mpassword,dusername,husername)
	flash("Car Status Successfully Changed !!!")
	return render_template("changecarstatus.html")

#---------------------DISPLAY DRIVER STATUS ---------------------------------------

@app.route("/displaydriverstatus/",methods=['GET','POST'])

def driverstatusdriver():
	cursor = conn.cursor()
	cursor.execute("""SELECT driverId,fName,lName,licence_no,status FROM Driver""")
	data1 = cursor.fetchall()
	cursor.close()
	
	return render_template("displaystatusdriver.html",data = data1)

#---------------------DISPLAY DRIVER STATUS ENDS---------------------------------------.

#---------------------Change DRIVER STATUS ---------------------------------------
@app.route("/changedriverstatus/",methods=['GET','POST'])

def changedriverstatusdriver():
	return render_template("changedriverstatus.html")

@app.route("/changedriverSTATUS/",methods=['GET','POST'])

def changedriverstatus():
	cdflag1 = False
	status_type = ['Available','Booked']
	Car_Type = ""
	cursor = conn.cursor()
	driverid = request.form["driverid"]
	driverid2 = int(driverid)
	cursor.execute("""SELECT driverId FROM Driver WHERE driverId = %s""",[driverid])
	did = cursor.fetchall()
	did_list = list(did)
	did_len = len(did_list)
	print("DID LIST",did_list)
	print("DRIVER ID :",driverid)
	for a in range(0,did_len):
		if did_list[a][0] == driverid2:
			cdflag1 = True
	if cdflag1 == False:
		flash("Entered DriverID is Invalid !!!")
		return render_template("changedriverstatus.html")
		
	Type = int(request.form["status"])
	status_Type = status_type[Type]
	
	cursor.execute("""UPDATE Driver SET status = %s WHERE driverId = %s""",(status_Type,driverid))
	conn.commit()
	cursor.close()
	#print(mpassword,dusername,husername)
	flash("Driver Status Successfully Changed !!!")
	return render_template("changedriverstatus.html")


#-----------------------------------------------------------------------------------------------------------------
@app.route('/pdf_download/',methods=['GET','POST'])
@login_required
def pdf_download():
	cursor = conn.cursor()
	
	print("CUSTID : ",custid)
	#user_id=request.form['user']
	cursor.execute("""SELECT carId FROM Booking WHERE bookingId = %s""",[b_actual_id])
	carr = cursor.fetchall()
	carrid = carr[0][0]
	#print(bookingid)
	
	cursor.execute("""SELECT model_name FROM Car WHERE car_id = %s""",[carrid])
	modell = cursor.fetchall()
	model = modell[0][0]
	
	#print(bookingId)
	#cursor.execute("""select Payment_id from Payment where status=%s and payment_type=%s""",(payment,payment_type))
	#pay=cursor.fetchall()
	#payment_id=pay[0][0]
	
	cursor.execute("""SELECT fName,lName FROM Cust_User where userId=%s""",[custid])
	#data5 = cursor.fetchall()
	data5 = cursor.fetchall()

	print(data5)
	data10=data5[0][0] +" "+data5[0][1]
	cursor.execute("""SELECT phone FROM Cust_User where userId=%s""",[custid])
	p_no=cursor.fetchall()
	p_no1=p_no[0][0]
	print(p_no)
	cursor.execute("""SELECT Cab,startdate,endDate,Pickup_time,Pickup_location,Drop_off_location FROM Booking where bookingId=%s""",[b_actual_id])
	union=cursor.fetchall()
	Cab=union[0][0]
	Sd=union[0][1]
	Ed=union[0][2]
	P_time=union[0][3]
	P_loc=union[0][4]
	D_loc=union[0][5]
	cursor.execute("""SELECT driverId FROM Booking where  bookingId=%s""",[b_actual_id])
	d_id=cursor.fetchall()
	driverid=d_id[0][0]
	cursor.execute("""SELECT fName,lName FROM Driver where driverId=%s""",[driverid])
	d_name=cursor.fetchall()
	d_full_name=d_name[0][0]+" "+d_name[0][1]
	cursor.execute("""SELECT phone_no FROM Driver where driverId=%s""",[driverid])
	dphone = cursor.fetchall()
	dphoneno = dphone[0][0]
	cursor.execute("""SELECT payment_type  FROM Payment where bookingId=%s""",[b_actual_id])
	pType=cursor.fetchall()
	print("PTYPE",pType)
	P_type=pType[0][0]
	
	cursor.execute("""SELECT total_amount FROM Payment where bookingId=%s""",[b_actual_id])
	amt1=cursor.fetchall()
	amt=amt1[0][0]
	
	html =  render_template("invoice.html",data = b_actual_id,name=data10,cab=Cab,cab_model=model,sd=Sd,ed=Ed,p_time=P_time,p_loc=P_loc,d_loc=D_loc,dName=d_full_name,dphone1=dphoneno,p_type=P_type,amount = amt)
	return render_pdf(HTML(string=html))

#------------------------------------------------STATUS PAGE--------------------------------------------------
@app.route('/status/',methods=['GET','POST'])

def statusdriver():
	most_used_route = ""
	cursor = conn.cursor()
	cursor.execute("""SELECT COUNT(*) FROM Cust_User""")
	total_c = cursor.fetchall()
	total_cust = total_c[0][0]
	cursor.execute("""SELECT COUNT(*) FROM Car""")
	total_ca = cursor.fetchall()
	total_car1 = total_ca[0][0]
	cursor.execute("""SELECT COUNT(*) FROM Car""")
	total_ca = cursor.fetchall()
	total_car1 = total_ca[0][0]
	cursor.execute("""SELECT COUNT(*) FROM Admin_User""")
	total_a = cursor.fetchall()
	total_admin = int(total_a[0][0])
	cursor.execute("""SELECT COUNT(*) FROM Driver""")
	total_d = cursor.fetchall()
	total_driver = int(total_d[0][0])
	total_employ = total_driver + total_admin
	cursor.execute("""SELECT COUNT(*) FROM Car WHERE status = 'Available' """)
	cart = cursor.fetchall()
	tcar = cart[0][0]
	cursor.execute("""SELECT COUNT(*) FROM Driver WHERE status = 'Available' """)
	drivert = cursor.fetchall()
	drivert = drivert[0][0]
	cursor.execute("""SELECT COUNT(*) FROM Booking""")
	tbook = cursor.fetchall()
	tbooking = tbook[0][0]
	cursor.execute("""SELECT COUNT(*) FROM Booking WHERE cab_route = 'Nashik-Pune' """)
	NP = cursor.fetchall()
	NProute = int(NP[0][0])
	cursor.execute("""SELECT COUNT(*) FROM Booking WHERE cab_route = 'Nashik-Nagpur' """)
	NN = cursor.fetchall()
	NNroute = int(NN[0][0])
	cursor.execute("""SELECT COUNT(*) FROM Booking WHERE cab_route = 'Nashik-Mumbai' """)
	NM = cursor.fetchall()
	NMroute = int(NM[0][0])
	cursor.execute("""SELECT COUNT(*) FROM Booking WHERE cab_route = 'Nashik-Aurangabad' """)
	NA = cursor.fetchall()
	NAroute = int(NA[0][0])
	cursor.execute("""SELECT COUNT(*) FROM Booking WHERE cab_route = 'Nashik-Dhule' """)
	ND = cursor.fetchall()
	NDroute = int(ND[0][0])
	if NProute > NNroute and NProute > NMroute and NProute > NAroute and NProute > NDroute:
		most_used_route = "Nashik-Pune"
	elif NNroute > NProute and NNroute > NMroute and NNroute > NAroute and NNroute > NDroute:
		most_used_route = "Nashik-Nagpur"
	elif NMroute > NNroute and NMroute > NProute and NMroute > NAroute and NMroute > NDroute:
		most_used_route = "Nashik-Mumbai"
	elif NAroute > NNroute and NAroute > NMroute and NAroute > NProute and NAroute > NDroute:
		most_used_route = "Nashik-Aurangabad"
	elif NDroute > NNroute and NDroute > NMroute and NDroute > NAroute and NDroute > NProute:
		most_used_route = "Nashik-Dhule"

	cursor.execute("SELECT COALESCE(SUM(total_amount), 0) FROM Payment")
	row = cursor.fetchone() or (0,)
	tsum = int(row[0])
	print("TOTAL CUST",total_cust)
	return render_template('Status.html',total = total_cust,tcar=total_car1,total_e=total_employ,total_car = tcar,total_driver=drivert,total_booking=tbooking,mroute=most_used_route,total_sum1=tsum)

@app.route('/allbooked/',methods=['GET','POST'])
def allbooked():
	print("Entered") 	#Testing
	
	return render_template("allbooked.html")


@app.route('/booked/',methods=['GET','POST'])
def booked():
	return redirect("/")
	
	
@app.route('/lastpage/',methods=['GET','POST'])

def lastpage():
	print("Entered") 	#Testing
	
	return render_template("final.html")
	
if __name__ == "__main__":
    # listen on all interfaces so Docker can route in
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

	