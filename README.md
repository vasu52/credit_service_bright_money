# CreditService

CreditService is a Django application designed to facilitate efficient lending by a loan provider to users. It provides functionalities for user registration, loan applications, repayment processing, billing, and fetching transaction statements.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [API Endpoints](#api-endpoints)

## Features

- User registration and credit score calculation
- Loan application processing
- Payment processing for EMIs
- Monthly billing
- Transaction statements and future dues retrieval
- Asynchronous tasks using Celery
- Periodic tasks using Celery Beat
- Redis as message brocker for Celery
- Atomic transactions to avoid race conditions

## Installation

1. Clone the repository:

    ```sh
    git clone https://github.com/vasu52/credit_service_bright_money.git
    cd credit_service_bright_money
    ```
    
2. Install the required packages:

    ```sh
    pip install django djangorestframework celery redis pandas django-celery-beat
    ```

3. Set up the database:

    ```sh
    python manage.py makemigrations
    python manage.py migrate
    ```

4. Run Redis:

    ```sh
    cd go_to_redis_directory
    redis-server.exe redis.windows.conf
    redis.cli
    ```
    
5. Run Celery worker (for windows):

    ```sh
    celery -A bright_money worker --pool=solo -l info
    ```
    For other than windows:
   ```sh
   celery -A bright_money worker -l info
   ```

7. Run Celery beat:

    ```sh
    celery -A bright_money beat -l info
    ```

8. Run the development server:

    ```sh
    python manage.py runserver
    ```

## API Endpoints

### User Registration

- **Endpoint:** `/api/register-user`
- **Method:** `POST`
- **Request Fields:**
  - `id`: User's id (if user is present in the transactions.csv file)
  - `aadhar_id`: User's Aadhar ID
  - `name`: User's name
  - `email_id`: User's email
  - `annual_income`: User's annual income
- **Response Fields:**
  - `user-details`: A JSON object containing all the user details

### Loan Application

- **Endpoint:** `/api/apply-loan`
- **Method:** `POST`
- **Request Fields:**
  - `user`: UUID of the user
  - `loan_type`: Type of the loan
  - `loan_amount`: Amount of the   loan
  - `interest_rate`: Interest rate for the loan
  - `term_period`: Term period in months
  - `disbursement_date`: Date of loan disbursement
- **Response Fields:**
  - `loan-details`: JSON of Loan details
  - `upcoming_trasactions`: List of EMI dates and corresponding amounts

### Payment

- **Endpoint:** `/api/make-payment`
- **Method:** `POST`
- **Request Fields:**
  - `loan_id`: Unique identifier for the loan
  - `amount`: Payment amount
- **Response Fields:**
  - `message`: Payment status message

### Statement

- **Endpoint:** `/api/get-statement?loan_id=<loan_id>`
- **Method:** `GET`
- **Response Fields:**
  - `principal-due`: Total Principal Amount due,
  - `interest-due`: Total Interest due,
  - `amount-paid`: Total amount paid till now, 
  - `past_transactions`: List of past transactions
  - `upcoming_transactions`: List of upcoming EMIs
