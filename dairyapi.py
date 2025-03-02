from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from datetime import timedelta, datetime,timezone
import mysql.connector
import jwt
from typing import Optional

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        passwd="mysql123",
        database="dairy"
    )

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

SECRET_KEY = "naveen"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

class Item(BaseModel):
    name: str
    description: str
    date: str
    image: str
    location: str

class User(BaseModel):
    username: EmailStr
    password: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception

        expire = payload.get("exp")
        if expire and datetime.utcnow() > datetime.fromtimestamp(expire):
            raise HTTPException(status_code=401, detail="Token has expired")

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT uid, username FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        db.close()

        if user is None:
            raise credentials_exception
        return {"Authorization": f"Bearer {token}", "user": user}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError as e:
        print(f"JWT Error: {e}")
        raise credentials_exception

@app.post("/signup")
async def signup(user: User):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
    if cursor.fetchone():
        cursor.close()
        db.close()
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = pwd_context.hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, password, created_date) VALUES (%s, %s, %s)",
        (user.username, hashed_password, datetime.now())
    )
    db.commit()
    cursor.close()
    db.close()
    return {"message": "User created successfully"}

@app.post("/login")
async def login(user: User):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
    db_user = cursor.fetchone()
    cursor.close()
    db.close()

    if not db_user or not pwd_context.verify(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/dairy")
async def create_dairy(entry: Item, current_user: dict = Depends(get_current_user)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    user_id = current_user["user"]["uid"]

    cursor.execute(
        "INSERT INTO dairy (name, description, date, image, location, user_id) VALUES (%s, %s, %s, %s, %s, %s)",
        (entry.name, entry.description, entry.date, entry.image, entry.location, user_id)
    )
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Dairy entry created successfully"}

@app.delete("/dairy/{dairy_id}")
async def delete_dairy(dairy_id: int, current_user: dict = Depends(get_current_user)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("DELETE FROM dairy WHERE user_id = %s AND dairy_id = %s", (current_user["user"]["uid"], dairy_id))
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Dairy entry deleted successfully"}


@app.get("/dairy")
async def get_dairy(current_user: dict = Depends(get_current_user)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM dairy WHERE user_id = %s", (current_user["user"]["uid"],))
    result = cursor.fetchall()
    cursor.close()
    db.close()

    if not result:
        return {"message": "No entries found"}

    return {"dairy": result}


@app.put("/dairy/{dairy_id}")
async def update_dairy(dairy_id: int, entry: Item, current_user: dict = Depends(get_current_user)):
    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    update_query = """
        UPDATE dairy 
        SET name = %s, description = %s, date = %s, image = %s, location = %s 
        WHERE user_id = %s AND dairy_id = %s
    """
    cursor.execute(
        update_query,
        (entry.name, entry.description, entry.date, entry.image, entry.location, current_user["user"]["uid"], dairy_id)
    )
    db.commit()
    cursor.close()
    db.close()
    return {"message": "Dairy entry updated successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
