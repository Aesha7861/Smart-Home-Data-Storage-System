import os
import mysql.connector
from flask_socketio import SocketIO
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
from pymongo import MongoClient
import logging
from datetime import datetime ,timedelta

from flask_bcrypt import Bcrypt
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = "smart_home_secret"
bcrypt = Bcrypt(app)

# MySQL Config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'  # Replace with your MySQL username
app.config['MYSQL_PASSWORD'] = 'root'  # Replace with your MySQL password
app.config['MYSQL_DB'] = 'smart_home'
app.config['SECRET_KEY'] = '7547'

mysql = MySQL(app)
socketio = SocketIO(app)

# Connect to MongoDB
mongo_client = MongoClient("mongodb://localhost:27017/")  # Replace with your MongoDB URI
mongo_db = mongo_client["smart_home"]  # Database name
sensors_collection = mongo_db["sensors"]  # Collection for storing sensor data


client = MongoClient("mongodb://localhost:27017/")
db = client.smart_home
sensors = db.sensors.find()


# Logging configuration
logging.basicConfig(level=logging.DEBUG)
# Routes

# Home Page
@app.route('/')
def index():
    return render_template('login.html')

@app.route('/test_connection')
def test_connection():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT DATABASE()")
        db_name = cur.fetchone()
        cur.close()
        return f"Connected to database: {db_name[0]}"
    except Exception as e:
        return f"Error: {e}"


def admin_required(f):
    def wrapper(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'admin':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

@app.route('/notifications')
def get_notifications():
    if 'logged_in' in session:
        user_id = session['user_id']
        
        cur = mysql.connection.cursor()
        # Fetch only unread notifications
        cur.execute("SELECT NotificationID, Message, Timestamp FROM Notifications WHERE UserID = %s AND IsRead = FALSE", [user_id])
        notifications = cur.fetchall()
        cur.close()

        # Convert notifications to a list of dictionaries
        notifications_list = [
            {"id": n[0], "message": n[1], "timestamp": n[2]} for n in notifications
        ]
        
        return {"notifications": notifications_list}
    else:
        return {"error": "User not logged in"}, 401

@app.route('/notify', methods=['POST'])
def notify():
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    
    # Save notification to the database
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO Notifications (UserID, Message) VALUES (%s, %s)", (user_id, message))
    mysql.connection.commit()
    cur.close()
    
    # Emit notification to the client
    socketio.emit('new_notification', {'message': message}, broadcast=True)
    return {"message": "Notification sent"}, 200

# Fetch and Display Users
@app.route('/users', methods=['GET'])
def get_user():
    if 'logged_in' in session:
        user_id = session['user_id']  # Get the logged-in user's ID from the session

        # Fetch the user's details from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT UserID, Name, Email FROM Users WHERE UserID = %s", [user_id])
        user = cur.fetchone()
        cur.close()

        # Pass the user details to the template
        return render_template('users.html', user=user)
    else:
        flash('Please log in to view your details.', 'danger')
        return redirect(url_for('login'))

# Add a New User
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Users (Name, Email) VALUES (%s, %s)", (name, email))
        mysql.connection.commit()
        cur.close()
        flash('User Added Successfully!')
        return redirect(url_for('users'))
    return render_template('add_user.html')

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        cur.execute("UPDATE Users SET Name = %s, Email = %s WHERE UserID = %s", (name, email, user_id))
        mysql.connection.commit()
        cur.close()
        flash('User Updated Successfully!')
        return redirect(url_for('users'))
    cur.execute("SELECT * FROM Users WHERE UserID = %s", (user_id,))
    user = cur.fetchone()
    cur.close()
    return render_template('edit_user.html', user=user)

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Users WHERE UserID = %s", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('User Deleted Successfully!')
    return redirect(url_for('users'))

# Fetch and Display Houses
@app.route('/houses')
def houses():
    if 'logged_in' in session:
        user_id = session['user_id']  # Get the logged-in user's ID from the session
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT HouseID, Address FROM Houses")
        houses = cur.fetchall()  # Fetch all houses from the database
        cur.close()
        return render_template('houses.html', houses=houses)
    except Exception as e:
        return render_template('error.html', error=str(e))
    
# Fetch and Display Houses
@app.route('/houses_resident')
def houses_resident():
    if 'logged_in' in session:
        user_id = session['user_id']  # Get the logged-in user's ID from the session
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT HouseID, Address FROM Houses WHERE OwnerUserID = %s", [user_id])
        houses = cur.fetchall()  # Fetch all houses from the database
        cur.close()
        return render_template('houses.html', houses=houses)
    except Exception as e:
        return render_template('error.html', error=str(e))
    


@app.route('/edit_resident/<int:resident_id>', methods=['GET', 'POST'])
def edit_resident(resident_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        resident_name = request.form['resident_name']
        cur.execute("UPDATE Residents SET ResidentName = %s WHERE ResidentID = %s", (resident_name, resident_id))
        mysql.connection.commit()
        flash('Resident updated successfully!', 'success')
        return redirect(url_for('houses'))

    cur.execute("SELECT ResidentID, ResidentName FROM Residents WHERE ResidentID = %s", (resident_id,))
    resident = cur.fetchone()
    cur.close()
    return render_template('edit_resident.html', resident=resident)

@app.route('/delete_resident/<int:resident_id>', methods=['POST'])
def delete_resident(resident_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM Residents WHERE ResidentID = %s", (resident_id,))
    mysql.connection.commit()
    flash('Resident deleted successfully!', 'success')
    return redirect(url_for('dashboard'))




@app.route('/add_house', methods=['GET', 'POST'])
def add_house():
    if 'logged_in' not in session:
        flash('Please log in to add a house.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        address = request.form['address']
        user_id = session['user_id']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Houses (OwnerUserID, Address) VALUES (%s, %s)", (user_id, address))
        mysql.connection.commit()
        user_id = session['user_id']
        message = f"New house added to House ."
        create_notification(user_id, message)
        socketio.emit('notification', {'message': message}, to=user_id)
        cur.close()

        flash('House added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_house.html')

@app.route('/residents', methods=['GET'])
def get_residents():
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT r.ResidentID, r.ResidentName, h.Address, h.HouseID
            FROM Residents r
            JOIN Houses h ON r.HouseID = h.HouseID
        """)
        residents = cur.fetchall()
        cur.close()
        # Pass the residents' data to the template
        return render_template('residents.html', residents=residents)
    except Exception as e:
        return render_template('error.html', error=str(e)), 500

@app.route('/add_resident', methods=['GET', 'POST'])
def add_resident():
    if request.method == 'POST':
        house_id = request.form['house_id']
        resident_name = request.form['resident_name']
        
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Residents (ResidentName, HouseID) VALUES (%s, %s)", (resident_name, house_id))
        mysql.connection.commit()
        # Create a notification
        user_id = session['user_id']
        message = f"New resident '{resident_name}' added to House {house_id}."
        create_notification(user_id, message)

        cur.close()
        
        flash("Resident added successfully!", "success")
        return redirect(url_for('dashboard'))
    
    # Fetch houses to populate the dropdown
    cur = mysql.connection.cursor()
    cur.execute("SELECT HouseID, Address FROM Houses")
    houses = cur.fetchall()
    cur.close()
    
    # Debugging
    if not houses:
        print("No houses found in the database.")
    else:
        print(f"Houses found: {houses}")
    
    return render_template('add_resident.html', houses=houses)

@app.route('/house/<int:house_id>/residents', methods=['GET'])
def get_house_residents(house_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT ResidentID, ResidentName
            FROM Residents
            WHERE HouseID = %s
        """, (house_id,))
        residents = cur.fetchall()
        cur.close()
        return {"residents": [{"ResidentID": r[0], "ResidentName": r[1]} for r in residents]}
    except Exception as e:
        return {"error": str(e)}, 500

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("INSERT INTO Users (Name, Email, PasswordHash) VALUES (%s, %s, %s)", (name, email, hashed_password))
            mysql.connection.commit()
            cur.close()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Email already exists!', 'danger')
            cur.close()
            return redirect(url_for('register'))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Users WHERE Email = %s", [email])
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user[3], password):
            session['logged_in'] = True
            session['user_id'] = user[0]
            session['user_name'] = user[1]
            session['role'] = user[4]  # Store role in session
             # Redirect based on role
            if user[4] == 'admin':
                return redirect(url_for('dashboard'))
            elif user[4] == 'government':
                return redirect(url_for('send_mail'))
            elif user[4] == 'resident':
                return redirect(url_for('resident_dashboard'))        
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# Dashboard Route (for logged-in users)
# Dashboard Route (for logged-in users)


@app.route('/send_mail', methods=['GET', 'POST'])
def send_mail():
    if 'logged_in' not in session or session['role'] != 'government':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        recipient_id = request.form['ResidentID']
        content = request.form['content']
        sender_id = session['user_id']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO MailItems (ResidentID, SenderID, Content) VALUES (%s, %s, %s)",
                    (recipient_id, sender_id, content))
        mysql.connection.commit()
        cur.close()

        flash('Mail sent successfully!', 'success')
        return redirect(url_for('send_mail'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT UserID, Name FROM Users WHERE Role = 'resident'")
    residents = cur.fetchall()
    cur.close()

    return render_template('send_mail.html', residents=residents)

# Route for residents to view their mail
@app.route('/view_mail')
def view_mail():
    if 'logged_in' not in session or session['role'] != 'resident':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('login'))
    user_id = session['user_id']

    cur = mysql.connection.cursor()
    cur.execute("SELECT Content,  Timestamp FROM mailitems WHERE ResidentID = %s", [user_id])
    mail_items = cur.fetchall()
    print(mail_items)
    cur.close()

    return render_template('view_mail.html', mail_items=mail_items)




def resident_required(f):
    def wrapper(*args, **kwargs):
        if 'logged_in' not in session or session.get('role') != 'resident':
            flash('Access denied. Residents only.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper


@app.route('/resident_dashboard')
@resident_required
def resident_dashboard():
    user_id = session['user_id']  # Logged-in resident's ID
    cur = mysql.connection.cursor()

        # Fetch user details
    cur.execute("SELECT Name, Email FROM Users WHERE UserID = %s", [user_id])
    user_details = cur.fetchone()

    cur = mysql.connection.cursor()

    # Fetch notifications for the logged-in resident
    cur.execute("SELECT NotificationID, Message, Timestamp FROM Notifications WHERE UserID = %s", [user_id])
    notifications = cur.fetchall()

    # Fetch sensors associated with the resident's houses
    cur.execute("""
        SELECT Sensors.SensorID, Sensors.Type, Sensors.Status, BaseStations.Name AS BaseStationName
        FROM Sensors
        INNER JOIN BaseStations ON Sensors.BaseStationID = BaseStations.BaseStationID
        INNER JOIN Houses ON BaseStations.UserID = Houses.OwnerUserID
        WHERE Houses.OwnerUserID = %s
    """, [user_id])
    sensors = cur.fetchall()

    # Fetch events linked to sensors or appliances
    cur.execute("""
        SELECT Events.EventID, Events.Timestamp, Events.EventDescription, Sensors.Type AS SensorType, Appliances.Name AS ApplianceName
        FROM Events
        LEFT JOIN Sensors ON Events.SensorID = Sensors.SensorID
        LEFT JOIN Appliances ON Events.ApplianceID = Appliances.ApplianceID
        WHERE Sensors.BaseStationID IN (SELECT BaseStationID FROM BaseStations WHERE UserID = %s)
           OR Appliances.HouseID IN (SELECT HouseID FROM Houses WHERE OwnerUserID = %s)
    """, [user_id, user_id])
    events = cur.fetchall()

    # Fetch appliances in the resident's houses
    cur.execute("""
        SELECT Appliances.ApplianceID, Appliances.Name, Appliances.Status, Houses.Address
        FROM Appliances
        INNER JOIN Houses ON Appliances.HouseID = Houses.HouseID
        WHERE Houses.OwnerUserID = %s
    """, [user_id])
    appliances = cur.fetchall()

    cur.execute("SELECT MailId, Content, Timestamp FROM mailitems WHERE ResidentID = %s", [session['user_id']])
    items = cur.fetchall()

    cur.close()

    return render_template(
        'resident_dashboard.html',
        notifications=notifications,
        sensors=sensors,
        events=events,
        appliances=appliances
    )

@app.route('/dashboard')
def dashboard():
    if 'logged_in' in session:
        user_role = session['role']

        # Redirect based on user role first
        if user_role == 'resident':
           return resident_dashboard()
        
        # Proceed if role is neither admin nor resident (default case)
        user_id = session['user_id']  # Get the logged-in user's ID from the session

        cur = mysql.connection.cursor()

        # Fetch user details
        cur.execute("SELECT Name, Email FROM Users WHERE UserID = %s", [user_id])
        user_details = cur.fetchone()

        # Fetch houses owned by the user
        cur.execute("SELECT HouseID, Address FROM Houses")
        houses = cur.fetchall()

        cur.execute("SELECT COUNT(*) FROM Notifications WHERE UserID = %s AND IsRead = FALSE", [user_id])
        unread_notifications = cur.fetchone()[0]

        # Fetch residents for each house owned by the user
        residents = []
        for house in houses:
            cur.execute("SELECT ResidentID, ResidentName FROM Residents WHERE HouseID = %s", [house[0]])
            house_residents = cur.fetchall()
            residents.append({"house_id": house[0], "residents": house_residents})

        # Count BaseStations owned by the user
        cur.execute("SELECT COUNT(*) FROM BaseStations WHERE UserID = %s", [user_id])
        basestations_count = cur.fetchone()[0]

        # Fetch BaseStations
        cur.execute("SELECT BaseStationID, Name, Location FROM BaseStations WHERE UserID = %s", [user_id])
        basestations = cur.fetchall()

        # Count Sensors linked to the user's BaseStations
        cur.execute("""
            SELECT COUNT(*) 
            FROM Sensors 
            INNER JOIN BaseStations ON Sensors.BaseStationID = BaseStations.BaseStationID 
            WHERE BaseStations.UserID = %s
        """, [user_id])
        sensors_count = cur.fetchone()[0]

        # Count Appliances linked to the user's Houses
        cur.execute("""
            SELECT COUNT(*) 
            FROM Appliances 
            INNER JOIN Houses ON Appliances.HouseID = Houses.HouseID 
            WHERE Houses.OwnerUserID = %s
        """, [user_id])
        appliances_count = cur.fetchone()[0]

        # Count Events
        cur.execute("""
            SELECT COUNT(*) 
            FROM Events 
            LEFT JOIN Sensors ON Events.SensorID = Sensors.SensorID 
            LEFT JOIN Appliances ON Events.ApplianceID = Appliances.ApplianceID
        """)
        events_count = cur.fetchone()[0]

        # Fetch Notifications
        cur.execute("SELECT NotificationID, Message, Timestamp FROM Notifications WHERE UserID = %s AND IsRead = 0", [user_id])
        notifications = cur.fetchall()

        cur.close()

        # Pass all data to the dashboard template
        return render_template(
            'dashboard.html',
            user=user_details,
            houses=houses,
            residents=residents,
            basestations_count=basestations_count,
            sensors_count=sensors_count,
            appliances_count=appliances_count,
            events_count=events_count,
            notifications=notifications  # Pass notifications to the template
        )

    else:
        flash('Please log in to access your dashboard.', 'danger')
        return redirect(url_for('login'))


def send_scheduled_notifications():
    cur = mysql.connection.cursor()
    cur.execute("SELECT UserID, Message FROM Notifications WHERE IsRead = FALSE")
    notifications = cur.fetchall()

    for notification in notifications:
        socketio.emit('new_notification', {'message': notification[1]}, room=notification[0])

    cur.close()

# Schedule the job to run every 10 minutes
#scheduler = BackgroundScheduler()
#scheduler.add_job(send_scheduled_notifications, 'interval', minutes=10)
#scheduler.start()


@app.route('/assign_appliance', methods=['POST'])
def assign_appliance():
    if 'logged_in' not in session:
        flash('Please log in to assign appliances.', 'danger')
        return redirect(url_for('login'))

    resident_id = request.form['resident_id']
    appliance_id = request.form['appliance_id']
    interval = request.form.get('interval', 60)  # Default to 60 minutes

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO NotificationPreferences (ResidentID, ApplianceID, NotificationInterval) 
        VALUES (%s, %s, %s)
    """, (resident_id, appliance_id, interval))
    mysql.connection.commit()
    cur.close()

    flash('Appliance assigned successfully!', 'success')
    return redirect(url_for('dashboard'))


@app.route('/assignments')
def view_assignments():
    if 'logged_in' not in session:
        flash('Please log in.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT ResidentID, ResidentName FROM Residents")
    residents = cur.fetchall()

    cur.execute("SELECT ApplianceID, Name FROM Appliances")
    appliances = cur.fetchall()
    cur.close()

    return render_template('assignments.html', residents=residents, appliances=appliances)


w

@app.route('/resident_notifications')
def resident_notifications():
    if 'logged_in' in session and session.get('role') == 'resident':
        user_id = session['user_id']

        cur = mysql.connection.cursor()
        cur.execute("SELECT Message, Timestamp FROM Notifications WHERE UserID = %s", [user_id])
        notifications = cur.fetchall()
        cur.close()

        return render_template('resident_notifications.html', notifications=notifications)
    else:
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))



@app.route('/notifications')
def view_notifications():
    if 'logged_in' in session:
        user_id = session['user_id']
        cur = mysql.connection.cursor()
        cur.execute("SELECT Message, Timestamp FROM Notifications WHERE UserID = %s ORDER BY Timestamp DESC", [user_id])
        notifications = cur.fetchall()
        cur.close()
        return render_template('notifications.html', notifications=notifications)
    else:
        flash("Please log in to view notifications.", "danger")
        return redirect(url_for('login'))


#scheduler = BackgroundScheduler()

# Example job function
def send_resident_notification():
    print("Sending resident notification...")

# Schedule the job with the correct trigger
#scheduler.add_job(send_resident_notification, 'interval', seconds=60)

#scheduler.start()



@app.route('/notifications/mark_read', methods=['POST'])
def mark_notifications_as_read():
    if 'logged_in' in session:
        user_id = session['user_id']  # Get the logged-in user's ID from the session
        
        # Get notification IDs from the request
        notification_ids = request.json.get('notification_ids', [])

        if not notification_ids:
            return {"error": "No notifications provided"}, 400

        cur = mysql.connection.cursor()
        # Update the `IsRead` status for the provided notification IDs
        cur.execute("UPDATE Notifications SET IsRead = TRUE WHERE UserID = %s AND NotificationID IN (%s)" % (user_id, ','.join(map(str, notification_ids))))
        mysql.connection.commit()
        cur.close()

        return {"message": "Notifications marked as read"}, 200
    else:
        return {"error": "User not logged in"}, 401


@app.route('/add_basestation', methods=['GET', 'POST'])
def add_basestation():
    if 'logged_in' not in session:
        flash('Please log in to add a BaseStation.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        location = request.form['location']
        user_id = session['user_id']

        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO BaseStations (Name, Location, UserID) VALUES (%s, %s, %s)", (name, location, user_id))
        mysql.connection.commit()
        # Create a notification
        user_id = session['user_id']
        message = f"New basestation '{name}' added ."
        create_notification(user_id, message)

        cur.close()

        flash('BaseStation added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_basestation.html')

@app.route('/basestations')
def view_basestations():
    if 'logged_in' not in session:
        flash('Please log in to view BaseStations.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']

    cur = mysql.connection.cursor()
    cur.execute("SELECT BaseStationID, Name, Location FROM BaseStations WHERE UserID = %s", [user_id])
    basestations = cur.fetchall()
    cur.close()

    return render_template('basestations.html', basestations=basestations)



@app.route('/add_sensor', methods=['GET', 'POST'])
def add_sensor():
    if 'logged_in' not in session:
        flash('Please log in to add a sensor.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT BaseStationID, Name FROM BaseStations WHERE UserID = %s", [session['user_id']])
    basestations = cur.fetchall()

    if request.method == 'POST':
        sensor_type = request.form['type']
        status = request.form['status']
        basestation_id = request.form['basestation_id']

        cur.execute("INSERT INTO Sensors (Type, Status, BaseStationID) VALUES (%s, %s, %s)", (sensor_type, status, basestation_id))
        mysql.connection.commit()
        cur.close()

        flash('Sensor added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_sensor.html', basestations=basestations)

@app.route('/basestation/<int:basestation_id>/sensors')
def view_sensors_by_basestation(basestation_id):
    if 'logged_in' not in session:
        flash('Please log in to view sensors.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT SensorID, Type, Status 
        FROM Sensors 
        WHERE BaseStationID = %s
    """, [basestation_id])
    sensors = cur.fetchall()
    cur.close()

    return render_template('sensors_by_basestation.html', sensors=sensors, basestation_id=basestation_id)































@app.route('/add_appliance', methods=['GET', 'POST'])
def add_appliance():
    if 'logged_in' not in session:
        flash('Please log in to add an appliance.', 'danger')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT HouseID, Address FROM Houses WHERE OwnerUserID = %s", [session['user_id']])
    houses = cur.fetchall()

    if request.method == 'POST':
        name = request.form['name']
        status = request.form['status']
        house_id = request.form['house_id']

        cur.execute("INSERT INTO Appliances (Name, Status, HouseID, AddedBy) VALUES (%s, %s, %s, %s)",
                    (name, status, house_id, session['user_id']))
        user_id = session['user_id']
        message = f"New basestation '{name}' added ."
        create_notification(user_id, message)
        mysql.connection.commit()
        cur.close()

        flash('Appliance added successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_appliance.html', houses=houses)



@app.route('/appliances')
def view_appliances():
    if 'logged_in' not in session:
        flash('Please log in to view appliances.', 'danger')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user_role = session['role']

    cur = mysql.connection.cursor()

    # If the user is an admin, fetch all appliances
    if user_role == 'admin':
        cur.execute("""
            SELECT a.ApplianceID, a.Name, a.Status, h.Address, u.Name AS AddedBy
            FROM Appliances a
            INNER JOIN Houses h ON a.HouseID = h.HouseID
            INNER JOIN Users u ON a.AddedBy = u.UserID
        """)

    else:
        # If the user is a resident, only fetch appliances for their houses
        cur.execute("""
            SELECT a.ApplianceID, a.Name, a.Status, h.Address, u.Name AS AddedBy
            FROM Appliances a
            INNER JOIN Houses h ON a.HouseID = h.HouseID
            INNER JOIN Users u ON a.AddedBy = u.UserID
            WHERE h.OwnerUserID = %s
        """, (user_id,))
    
    appliances = cur.fetchall()
    cur.close()

    print(appliances)

    return render_template('appliances.html', appliances=appliances)


@app.route('/add_event', methods=['GET', 'POST'])
def add_event():
    if 'logged_in' not in session:
        flash('Please log in to log an event.', 'danger')
        return redirect(url_for('login'))

    
    cur = mysql.connection.cursor()
    cur.execute("SELECT SensorID, Type FROM Sensors")
    sensors = cur.fetchall()

    cur.execute("SELECT ApplianceID, Name FROM Appliances")
    appliances = cur.fetchall()

    if request.method == 'POST':
        description = request.form['description']
        sensor_id = request.form.get('sensor_id')
        appliance_id = request.form.get('appliance_id')

        cur.execute("INSERT INTO Events (EventDescription, SensorID, ApplianceID) VALUES (%s, %s, %s)", (description, sensor_id, appliance_id))
        mysql.connection.commit()
        cur.close()

        flash('Event logged successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('add_event.html', sensors=sensors, appliances=appliances)

@app.route('/events')
def view_events():
    if 'logged_in' not in session:
        flash('Please log in to view events.', 'danger')
        return redirect(url_for('login'))
    user_id = session.get('user_id')
    user_role = session.get('role')
    def redirect_dashboard():
            if user_role == 'admin':
                return redirect(url_for('dashboard'))
            elif user_role == 'resident':
                return redirect(url_for('resident_dashboard'))
            else:
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('login'))
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT Events.EventID, Events.Timestamp, Events.EventDescription, Sensors.Type, Appliances.Name
        FROM Events
        LEFT JOIN Sensors ON Events.SensorID = Sensors.SensorID
        LEFT JOIN Appliances ON Events.ApplianceID = Appliances.ApplianceID
    """)
    events = cur.fetchall()
    cur.close()

    return render_template('events.html', events=events)

@app.route('/add_sensor_data', methods=['POST'])
def add_sensor_data():
    if request.method == 'POST':
        data = {
            "sensor_id": request.json.get("sensor_id"),
            "type": request.json.get("type"),
            "status": request.json.get("status"),
            "value": request.json.get("value"),
            "unit": request.json.get("unit"),
            "timestamp": request.json.get("timestamp"),
            "basestation_id": request.json.get("basestation_id")
        }

        sensors_collection.insert_one(data)  # Insert the document into MongoDB
        return {"message": "Sensor data added successfully!"}, 201



@app.route('/api/test_notification', methods=['GET'])
def test_notification():
    if 'user_id' in session:
        user_id = session['user_id']
        create_notification(user_id, "This is a test notification!")
        return jsonify({"message": "Notification added!"}), 200
    else:
        return jsonify({"error": "User not logged in"}), 401





@app.route('/get_sensor_data', methods=['GET'])
def get_sensor_data():
    sensor_data = list(sensors_collection.find({}, {"_id": 0}))  # Exclude MongoDB's internal _id field
    return {"sensors": sensor_data}, 200


@app.route('/get_sensors_by_basestation/<basestation_id>', methods=['GET'])
def get_sensors_by_basestation(basestation_id):
    sensor_data = list(sensors_collection.find({"basestation_id": basestation_id}, {"_id": 0}))
    return {"sensors": sensor_data}, 200


@app.route('/api/get_appliances', methods=['GET'])
def get_appliances():
    if 'logged_in' not in session:
        return jsonify({"error": "Unauthorized access"}), 401
    

    user_id = session.get('user_id')
    user_role = session.get('role')
    def redirect_dashboard():
            if user_role == 'admin':
                return redirect(url_for('dashboard'))
            elif user_role == 'resident':
                return redirect(url_for('resident_dashboard'))
            else:
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if user_role == 'resident':
        # Fetch house ID for the resident
        cur.execute("SELECT HouseID FROM Houses WHERE OwnerUserID = %s", [user_id])
        house = cur.fetchone()
        if not house:
            return jsonify({"error": "No house assigned to the user"}), 404

        house_id = house[0]

        # Fetch appliances for the resident's house
        cur.execute("""
            SELECT ApplianceID, Name, Status 
            FROM Appliances 
            WHERE HouseID = %s
        """, [house_id])
    elif user_role == 'admin':
        # Admin can view all appliances
        cur.execute("""
            SELECT ApplianceID, Name, Status, HouseID 
            FROM Appliances
        """)
    else:
        return jsonify({"error": "Unauthorized access"}), 403

    appliances = cur.fetchall()
    cur.close()

    appliance_list = [
        {
            "ApplianceID": appliance[0],
            "Name": appliance[1],
            "Status": appliance[2],
            "HouseID": appliance[3] if user_role == 'admin' else house_id
        }
        for appliance in appliances
    ]

    return jsonify({"appliances": appliance_list})



# Helper functions
def get_user_by_house(house_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT OwnerUserID FROM Houses WHERE HouseID = %s", (house_id,))
        result = cur.fetchone()
        cur.close()
        
        if result:
            return result[0]  # Return the OwnerUserID
        else:
            return None  # No matching house found

    except Exception as e:
        logging.error(f"Error retrieving user by house: {e}")
        return None


def create_notification(user_id, message):
    try:
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO Notifications (UserID, Message, IsRead) VALUES (%s, %s, FALSE)", (user_id, message))
        mysql.connection.commit()
        cur.close()
        logging.info(f"Notification inserted for User ID: {user_id} with message: {message}")
    except Exception as e:
        logging.error(f"Error inserting notification: {e}")



@app.route('/create_personalized_notification', methods=['GET', 'POST'])
def create_personalized_notification():
    if 'logged_in' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            user_id = request.form['user_id']
            notification_type = request.form['notification_type']
            message = request.form['message']
            interval = request.form['interval']

            # Insert the notification into the database with interval
            cur = mysql.connection.cursor()
            cur.execute(
                "INSERT INTO Notifications (UserID, Message, IsRead, Time_Interval) VALUES (%s, %s, FALSE, %s)",
                (user_id, f"{notification_type}: {message}", interval)
            )
            mysql.connection.commit()
            cur.close()

            flash('Personalized notification sent successfully!', 'success')
            return redirect(url_for('dashboard'))

        # Fetch residents to assign notifications
        cur = mysql.connection.cursor()
        cur.execute("SELECT UserID, Name FROM Users WHERE Role = 'resident'")
        residents = cur.fetchall()
        cur.close()

        return render_template('create_personalized_notification.html', residents=residents)
    else:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('login'))



# Check sensor alerts
def check_sensor_alerts():
    logging.info("Running sensor alert check...")
    sensors = list(sensors_collection.find({"Value": {"$gt": 30}}))
    logging.debug(f"Found {len(sensors)} sensors exceeding threshold")

    for sensor in sensors:
        house_id = sensor['Metadata'].get('house_id')
        user_id = get_user_by_house(house_id)
        
        if user_id:
            message = f"Alert: Sensor {sensor['SensorID']} detected high value {sensor['Value']}!"
            create_notification(user_id, message)
            logging.info(f"Notification created for User ID: {user_id}")
        else:
            logging.warning(f"No user found for house ID: {house_id}")


def simulate_sensor_submission():
    sensor_data = {
        "SensorID": "Temp789",
        "BaseStationID": "3",
        "Value": random.uniform(20.0, 40.0),
        "Unit": "Celsius",
        "Timestamp": datetime.utcnow().isoformat(),
        "Status": "Active",
        "Metadata": {
            "location": "Kitchen",
            "sensor_type": "Temperature",
            "house_id": "5"
        }
    }
    
   # response = requests.post("http://127.0.0.1:5000/api/receive_sensor_data", json=sensor_data)
   # logging.info(f"Automated Sensor Data Sent: {sensor_data}, Response: {response.status_code}")

   # scheduler.add_job(simulate_sensor_submission, 'interval', seconds=60)
   # scheduler.start()


# Flask Routes
import logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/api/register_sensor', methods=['POST'])
def store_sensor_data():
    try:
        # Parse JSON request data
        data = request.json
        
        # Extract required fields
        sensor_id = data.get("SensorID")
        base_station_id = data.get("BaseStationID")
        timestamp = data.get("Timestamp", datetime.utcnow().isoformat())
        value = data.get("Value")
        status = data.get("Status")
        metadata = data.get("Metadata", {})
        house_id = data.get("HouseID")

        # Validate required fields
        if not sensor_id or not base_station_id or value is None or not house_id:
            return jsonify({"error": "Missing required fields"}), 400

        # Prepare sensor document to insert into MongoDB
        sensor_document = {
            "SensorID": sensor_id,
            "BaseStationID": base_station_id,
            "Timestamp": timestamp,
            "Value": value,
            "Status": status,
            "Metadata": metadata,
            "HouseID": house_id
        }

        # Insert the document into MongoDB
        sensors_collection.insert_one(sensor_document)

        return jsonify({"message": "Sensor data stored successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/receive_sensor_data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.json
        
        # Extract data from request
        sensor_id = data.get("SensorID")
        base_station_id = data.get("BaseStationID")
        value = data.get("Value")
        unit = data.get("Unit")
        timestamp = data.get("Timestamp") or datetime.utcnow().isoformat()
        status = data.get("Status")
        metadata = data.get("Metadata", {})

        # Validate required fields
        if not sensor_id or not base_station_id or value is None:
            return jsonify({"error": "Missing required fields"}), 400

        # Insert sensor data into MongoDB
        sensors_collection.insert_one({
            "SensorID": sensor_id,
            "BaseStationID": base_station_id,
            "Value": value,
            "Unit": unit,
            "Timestamp": timestamp,
            "Status": status,
            "Metadata": metadata
        })

        # Fetch the user associated with the house ID in metadata
        house_id = metadata.get("house_id")
        user_id = get_user_by_house(house_id)

        if user_id:
            notification_message = f"Sensor {sensor_id} recorded value {value} {unit} in {metadata.get('location')}."
            create_notification(user_id, notification_message)

        return jsonify({"message": "Sensor data saved successfully!"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    

    cur = mysql.connection.cursor()
    def redirect_dashboard():
            if user_role == 'admin':
                return redirect(url_for('dashboard'))
            elif user_role == 'resident':
                return redirect(url_for('resident_dashboard'))
            else:
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('login'))


@app.route('/sensors')
def view_sensors():
    try:
        user_id = session.get('user_id')
        user_role = session.get('role')

        if not user_id:
            flash('Please log in to view sensor data.', 'danger')
            return redirect(url_for('login'))

        # Fetch houses owned by the user
        cur = mysql.connection.cursor()
        if user_role == 'admin': 
            cur.execute("SELECT HouseID FROM Houses WHERE OwnerUserID = %s", [user_id])
        elif user_role == 'resident':
            cur.execute("SELECT h.HouseID FROM Houses as h , users as u WHERE  h.OwnerUserID = %s", [user_id])
        
        house_ids = cur.fetchall()
        
        house_id_list = [str(house[0]) for house in house_ids]
        print(house_id_list)
        cur.close()

        # Fetch sensor data from MongoDB
        sensors = list(sensors_collection.find({"HouseID": {"$in": house_id_list}}))
        for sensor in sensors:
            sensor['_id'] = str(sensor['_id'])

        return render_template('sensors.html', sensors=sensors)

    except Exception as e:
        flash(f"Error fetching sensor data: {e}", 'danger')
        return redirect(url_for('dashboard'))

""""
# APScheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(check_sensor_alerts, 'interval', seconds=3600)
scheduler.add_job(simulate_sensor_submission, 'interval', seconds=3600)
scheduler.start()
"""

def validate_event(data):
    if not data["title"] or not data["description"]:
        return "Title and Description are required."
    if data["start_time"] >= data["end_time"]:
        return "End time must be after start time."
    if data["recurrence"] not in ["None", "Daily", "Weekly", "Monthly"]:
        return "Invalid recurrence value."
    if data["access_level"] not in ["Private", "Shared"]:
        return "Invalid access level."
    return None


@app.route('/calendar')
def calendar():
    user_id = session.get('user_id')
    if not user_id:
        flash("Please log in first", "error")
        return redirect(url_for('login'))

    recurrence = request.args.get('recurrence', '')
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Adjust per-page limit as needed

    query = "SELECT ResidentID, HouseID, Title, Description, StartTime, EndTime, Recurrence, AccessLevel FROM calendar_events WHERE ResidentID = %s"
    params = [user_id]

    if recurrence:
        query += " AND Recurrence = %s"
        params.append(recurrence)

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM calendar_events WHERE ResidentID = %s", (user_id,))
    total_events = cur.fetchone()[0]

    query += " LIMIT %s OFFSET %s"
    params.extend([per_page, (page - 1) * per_page])

    cur.execute(query, params)
    events = cur.fetchall()
    cur.close()

    total_pages = (total_events // per_page) + (1 if total_events % per_page else 0)

    return render_template('calendar.html', events=events, recurrence=recurrence, page=page, total_pages=total_pages)



@app.route('/calendar/add', methods=['GET', 'POST'])
def add_calendar_event():
    if request.method == 'POST':
        data = request.form
        error = validate_event(data)
        if error:
            flash(error, 'error')
            return redirect(url_for('calendar'))

        cur = mysql.connection.cursor()
        query = """
            INSERT INTO calendar_events (ResidentID, HouseID, Title, Description, StartTime, EndTime, Recurrence, AccessLevel)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.execute(query, (
            session['user_id'], 
            data["house_id"], 
            data["title"], 
            data["description"], 
            data["start_time"], 
            data["end_time"], 
            data["recurrence"], 
            data["access_level"]
        ))
        mysql.connection.commit()
        cur.close()
        flash('Event added successfully!', 'success')
        return redirect(url_for('calendar'))
    
    # Render the 'add_event.html' form for GET requests
    return render_template('add_event.html')

@app.route('/calendar/resident/<int:resident_id>', methods=['GET'])
def get_events_by_resident(resident_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM calendar_events WHERE ResidentID = %s ORDER BY StartTime", (resident_id,))
    events = cur.fetchall()
    cur.close()
    return jsonify(events)

@app.route('/calendar/update/<int:event_id>', methods=['GET', 'POST'])
def update_event(event_id):
    cur = mysql.connection.cursor()
    if request.method == 'POST':
        data = request.form
        query = """
            UPDATE calendar_events
            SET Title=%s, Description=%s, StartTime=%s, EndTime=%s, Recurrence=%s, AccessLevel=%s
            WHERE EventID=%s
        """
        cur.execute(query, (
            data["title"], 
            data["description"], 
            data["start_time"], 
            data["end_time"], 
            data["recurrence"], 
            data["access_level"], 
            event_id
        ))
        mysql.connection.commit()
        cur.close()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('calendar'))
    
    cur.execute("SELECT * FROM calendar_events WHERE EventID = %s", (event_id,))
    event = cur.fetchone()
    cur.close()
    return render_template('update_event.html', event=event, event_id=event_id)

@app.route('/calendar/delete/<int:event_id>', methods=['POST'])
def delete_event(event_id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM calendar_events WHERE EventID = %s", (event_id,))
    mysql.connection.commit()
    cur.close()
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('calendar'))

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)