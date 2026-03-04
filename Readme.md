RinkalPatel1996: generate readme file for this project 

Workspace: Collecting workspace information

# Smart Home Management System

## Project Overview

The **Smart Home Management System** is designed to manage various aspects of a smart home, including users, houses, sensors, appliances, and notifications. The system ensures secure and efficient management of smart home data, providing different functionalities for residents, government officials, and administrators.

---

## Features

### 1. User Roles and Access Control

- **Residents:**
  - View and manage their houses, sensors, appliances, and events.
  - Receive and view notifications.
  - View their mail.

- **Government Officials:**
  - Send mail to residents.
  - View residents list.

- **Admin:**
  - Manage users, houses, sensors, appliances, and notifications.
  - Monitor system logs.

### 2. Smart Home Management

- **House Management:**
  - Add, view, and manage houses.
  - Assign residents to houses.

- **Sensor Management:**
  - Add, view, and manage sensors.
  - View sensor data.

- **Appliance Management:**
  - Add, view, and manage appliances.
  - Assign appliances to residents.

- **Event Management:**
  - Log and view events related to sensors and appliances.

### 3. Notifications

- **Real-time Notifications:**
  - Send and receive real-time notifications using Socket.IO.
  - Mark notifications as read.

### 4. Mail Management

- **Secure Mail Storage:**
  - Residents can view their received mail.
  - Government officials can send mail to residents.

### 5. User Authentication and Authorization

- **Secure Login/Logout:**
  - Role-based redirection.
  - Password hashing using bcrypt.
  - Session management to track authenticated users.

### 6. Security Features

- **Role-based Access Control (RBAC):**
  - Restrict unauthorized actions.
  - Input validation to prevent SQL injection and other attacks.

---

## Technologies Used

- **Backend:** Flask (Python), Flask-MySQL, Flask-SocketIO
- **Frontend:** HTML, CSS (Jinja templating)
- **Database:** MySQL, MongoDB
- **Security:** Bcrypt for password hashing, Flask-Session for session management
- **Deployment:** Docker, Gunicorn, Nginx (for production)

---

## Installation and Setup

### 1. Prerequisites

Ensure you have the following installed:

- Python (>=3.8)
- MySQL Server
- MongoDB Server
- Docker (optional but recommended)

### 2. Installation Steps

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/smart-home-management-system.git
   cd smart-home-management-system
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up MySQL and MongoDB databases:

   - Create a MySQL database named 

smart_home

.
   - Update the MySQL and MongoDB connection details in 

app.py

.

4. Run the Flask application:

   ```bash
   python app.py
   ```

5. Open the web application in your browser:

   ```bash
   http://127.0.0.1:5000
   ```

### 3. Docker Setup (Optional)

1. Build and run the Docker containers:

   ```bash
   docker-compose up --build
   ```

2. Open the web application in your browser:

   ```bash
   http://127.0.0.1:5000
   ```

---

## Usage Instructions

### Login to the system:

- Use the provided credentials or sign up.

### Resident Dashboard:

- View and manage houses, sensors, appliances, and events.
- View notifications and mail.
- Logout securely.

### Government Official Panel:

- Send mail to residents.
- View residents list.

### Admin Panel:

- Manage users, houses, sensors, appliances, and notifications.
- Monitor system logs.

---

## Contact

For any questions or support, please contact:

- Email: r.zadafiya@oth-aw.de
- GitHub: [https://git.oth-aw.de/6154/mdne](https://git.oth-aw.de/6154/mdne)