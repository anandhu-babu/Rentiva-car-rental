# Rentiva - Car Rental Platform

## Project Overview

Rentiva is a Django-based car rental platform that connects vehicle owners (Renters) with customers looking to rent vehicles. The platform provides vehicle listing, booking management, role-based dashboards, and an AI-powered chatbot assistant.

---

## Features

### User Authentication

* User Registration
* User Login and Logout
* Profile Management

### Customer Features

* Browse Available Cars
* View Car Details
* Search Cars by Location
* Book Vehicles
* Manage Profile

### Renter Features

* Add New Cars
* Edit Car Listings
* Delete Car Listings
* Manage Vehicle Inventory
* View Customer Bookings
* Access Renter Dashboard

### Admin Features

* Manage Users
* Manage Cars
* Manage Bookings
* Django Administration Panel

### AI Assistant

* Vehicle Recommendations
* Booking Guidance
* Rental Assistance

### Responsive Design

* Mobile Friendly Interface
* Tablet Compatibility
* Desktop Optimization

---

## Technologies Used

### Backend

* Python
* Django
* Django REST Framework

### Frontend

* HTML5
* CSS3
* JavaScript

### Database

* SQLite3

### Tools and Services

* Git
* GitHub
* Hugging Face API

---

## Project Structure

text
Rentiva/
│
├── CarRental/
│   ├── templates/
│   ├── static/
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   └── serializers.py
│
├── uploads/
├── manage.py
└── README.md


---

## Installation

### Clone Repository

bash
git clone https://github.com/anandhu-babu/Rentiva-car-rental.git

cd Rentiva-car-rental


### Create Virtual Environment

bash
python -m venv env


### Activate Virtual Environment

Windows:

bash
env\Scripts\activate


Linux / macOS:

bash
source env/bin/activate


### Install Dependencies

bash
pip install -r requirements.txt


### Apply Migrations

bash
python manage.py migrate


### Run Development Server

bash
python manage.py runserver


Open the application in a browser:

text
http://127.0.0.1:8000/


---

## API Endpoints

### Cars API

text
/api/cars/
/api/cars/add/


### Chatbot API

text
/api/chatbot/


---

## Screenshots

* Home Page
* Login Page
* Registration Page
* Car Details Page
* User Dashboard
* Renter Dashboard
* AI Chatbot Interface

---

## Learning Outcomes

This project demonstrates:

* Django Web Development
* Authentication and Authorization
* Role-Based Access Control
* CRUD Operations
* REST API Development
* Database Integration
* Responsive User Interface Design
* Git and GitHub Workflow

---

## Future Enhancements

* Online Payment Gateway Integration
* Google Maps Integration
* Vehicle Ratings and Reviews
* Email Notifications
* Advanced Search Filters
* Mobile Application

---

## Developer

Anandhu B

GitHub: https://github.com/anandhu-babu

---

## License

This project is developed for educational and portfolio purposes.
