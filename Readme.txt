
flow:-

user --> username/email  --> Validate User Request --> if user/pwd in db -> yes --> [JWT service] --> issue JWT token to user --> loged_in
         passward                                  --> if user/pwd not in db -> show(incorrect user/pwd)


        JWT token : {Token: , Expiry_Time:  }

        with every time user perform access any(rout/CRUD operation): [JWT service] checks - valid: 1. TOKEN          -> if Valid -> Allow Operation
                                                                                                                      -> if In_Valid -> Stop Operation, and Throw error. 
                                                                                                    2. Expiry_Time    -> if Token Expired -> JWT Service(Refresh_Token_Service) -> Issue New TOKEN    -> Allow Operation
                                                                                                                                                                                 & New Expiry_Time
Structure:-

JWT Service:
    - Issue_New_Token_Service:
    - Refresh_Token_Service:
    - Constantly_Checks_Token_Service:(checks tokens of all Loged_in users on any given time)

TO LEARN:-
Q1. HTML CSS frontend se, FAST API ko post Request Kaise bhejenge, {user/email, pwd} paramater ke sath.
    - Q1.1 FAST api main post request.
    - Q1.2 Fast api main request ko correct rout se map kaise karte hai ?
    - Q1.3 Fast api main db kaise connect karte hai ?
        - Q1.3.1 Fast api main db config {db_address: , db_pwd: } kaise store karte hai ?
        - Q1.3.2 fast api main db pe crud operation kaise karenge - ORM ya RAW_SQL ?

CHAT GPT GENERATED QUESTIONS :-

🔹 Q1. Frontend → FastAPI Request Flow
    Q1.1: HTML/CSS/JS se FastAPI ko POST request kaise bhejte?
    Q1.2: FastAPI me routes kaise create hote hain? (@app.post("/login"))
    Q1.3: Form-data vs JSON → FastAPI mein kaise handle karte hain?
    Q1.4: Request body ko validate kaise karte hain? → Pydantic models
    Q1.5: Response format standard kaise set karein?

🔹 Q2. Database Integration
    Q2.1: FastAPI se DB connect kaise karte hain? SQLite/MySQL/PostgreSQL
    Q2.2: DB credentials secure kaise store karte hain? .env, settings.py
    Q2.3: CRUD kaise karte hain? ORM (SQLAlchemy) vs Raw SQL — kab kya use?
    Q2.4: DB connection per request lifecycle? Dependency injection?
    Q2.5: Migration tool → Alembic kaise use hota hai?

🔹 Q3. User Authentication / JWT
    Q3.1: Login ke time password hash kaise karte hain?
    Q3.2: JWT issue kaise hota hai? (access_token, expiry)
    Q3.3: Har protected route par JWT kaise verify hota hai?
    Q3.4: Token expiry → auto refresh kaise implement hota?
    Q3.5: Logout / JWT blacklist kaise handle karte hain?

🔹 Q4. Project Structure — Production Standards
    Q4.1: routers, services, models, schemas ka folder structure?
    Q4.2: Config management — .env, settings classes?
    Q4.3: Background tasks? Celery?
    Q4.4: Middleware kya hota hai? Example use cases?

🔹 Q5. Security
    Q5.1: CORS kya hota hai? Frontend integration me kaise enable?
    Q5.2: Rate limiting? Brute force prevention?
    Q5.3: HTTPS / SSL setup kaise hota hai?

🔹 Q6. Validation + Error Handling
    Q6.1: Pydantic validations best practices?
    Q6.2: Custom errors and responses kaise banate hain?
    Q6.3: Global exception handlers?

🔹 Q7. Testing & Debugging
    Q7.1: FastAPI apps ke liye pytest kaise likhte hain?
    Q7.2: Fake DB / mock services kaise use karte hain?

🔹 Q8. Deployment
    Q8.1: Production server — Uvicorn/Gunicorn combo?
    Q8.2: Dockerization? Dockerfile best practices?
    Q8.3: Cloud deployment — Render / Railway / AWS / Azure / GCP?
    Q8.4: CI/CD automation (GitHub Actions)?


    