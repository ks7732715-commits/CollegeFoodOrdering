from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

app = Flask(__name__)

# =========================
# APPLICATION SETTINGS
# =========================

app.secret_key = os.getenv(
    "SECRET_KEY",
    "temporary-secret-key"
)


# =========================
# DATABASE CONNECTION
# =========================

db = mysql.connector.connect(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PASSWORD", ""),
    database=os.getenv("DB_NAME", "college_food")
)


# =========================
# ADMIN CHECK
# =========================

def is_admin():

    return (
        "user_id" in session
        and session.get("user_role") == "admin"
    )


# =========================
# HOME
# =========================

@app.route("/")
def home():

    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT * FROM food_items WHERE available = TRUE"
    )

    foods = cursor.fetchall()

    cursor.close()

    return render_template(
        "index.html",
        foods=foods
    )


# =========================
# REGISTER
# =========================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        if not name or not email or not password:
            return "All fields are required!"

        if len(password) < 6:
            return "Password must be at least 6 characters!"

        hashed_password = generate_password_hash(password)

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM users WHERE email = %s",
            (email,)
        )

        existing_user = cursor.fetchone()

        if existing_user:

            cursor.close()

            return "Email already registered!"

        cursor.execute(
            """
            INSERT INTO users
            (name, email, password)
            VALUES (%s, %s, %s)
            """,
            (
                name,
                email,
                hashed_password
            )
        )

        db.commit()

        cursor.close()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            "SELECT * FROM users WHERE email = %s",
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["user_role"] = user["role"]

            return redirect(
                url_for("home")
            )

        return "Invalid email or password!"

    return render_template(
        "login.html"
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("home")
    )


# =========================
# ADD TO CART
# =========================

@app.route("/add_to_cart/<int:food_id>")
def add_to_cart(food_id):

    if "cart" not in session:
        session["cart"] = {}

    cart = session["cart"]

    food_id = str(food_id)

    if food_id in cart:
        cart[food_id] += 1
    else:
        cart[food_id] = 1

    session["cart"] = cart
    session.modified = True

    return redirect(
        url_for("home")
    )


# =========================
# CART
# =========================

@app.route("/cart")
def cart():

    cart = session.get(
        "cart",
        {}
    )

    cart_items = []
    total = 0

    cursor = db.cursor(
        dictionary=True
    )

    for food_id, quantity in cart.items():

        cursor.execute(
            "SELECT * FROM food_items WHERE id = %s",
            (food_id,)
        )

        food = cursor.fetchone()

        if food:

            subtotal = (
                float(food["price"])
                * quantity
            )

            cart_items.append({
                "id": food["id"],
                "name": food["name"],
                "price": float(food["price"]),
                "quantity": quantity,
                "subtotal": subtotal
            })

            total += subtotal

    cursor.close()

    return render_template(
        "cart.html",
        cart_items=cart_items,
        total=total
    )


# =========================
# REMOVE FROM CART
# =========================

@app.route("/remove_from_cart/<int:food_id>")
def remove_from_cart(food_id):

    cart = session.get(
        "cart",
        {}
    )

    food_id = str(food_id)

    if food_id in cart:
        del cart[food_id]

    session["cart"] = cart
    session.modified = True

    return redirect(
        url_for("cart")
    )


# =========================
# CHECKOUT
# =========================

@app.route("/checkout")
def checkout():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    cart = session.get(
        "cart",
        {}
    )

    if not cart:

        return redirect(
            url_for("cart")
        )

    cart_items = []
    total = 0

    cursor = db.cursor(
        dictionary=True
    )

    for food_id, quantity in cart.items():

        cursor.execute(
            "SELECT * FROM food_items WHERE id = %s",
            (food_id,)
        )

        food = cursor.fetchone()

        if food:

            subtotal = (
                float(food["price"])
                * quantity
            )

            cart_items.append({
                "id": food["id"],
                "name": food["name"],
                "price": float(food["price"]),
                "quantity": quantity,
                "subtotal": subtotal
            })

            total += subtotal

    cursor.close()

    return render_template(
        "checkout.html",
        cart_items=cart_items,
        total=total
    )


# =========================
# PLACE ORDER
# =========================

@app.route("/place_order", methods=["POST"])
def place_order():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    cart = session.get(
        "cart",
        {}
    )

    if not cart:

        return redirect(
            url_for("cart")
        )

    cursor = db.cursor(
        dictionary=True
    )

    total = 0
    order_items = []

    for food_id, quantity in cart.items():

        cursor.execute(
            "SELECT * FROM food_items WHERE id = %s",
            (food_id,)
        )

        food = cursor.fetchone()

        if food:

            price = float(
                food["price"]
            )

            subtotal = (
                price * quantity
            )

            total += subtotal

            order_items.append({
                "food_id": food["id"],
                "quantity": quantity,
                "price": price
            })

    if not order_items:

        cursor.close()

        return redirect(
            url_for("cart")
        )

    cursor.execute(
        """
        INSERT INTO orders
        (user_id, total_amount, status)
        VALUES (%s, %s, %s)
        """,
        (
            session["user_id"],
            total,
            "Pending"
        )
    )

    order_id = cursor.lastrowid

    for item in order_items:

        cursor.execute(
            """
            INSERT INTO order_items
            (order_id, food_id, quantity, price)
            VALUES (%s, %s, %s, %s)
            """,
            (
                order_id,
                item["food_id"],
                item["quantity"],
                item["price"]
            )
        )

    db.commit()

    cursor.close()

    session["cart"] = {}

    return redirect(
        url_for(
            "order_success",
            order_id=order_id
        )
    )


# =========================
# ORDER SUCCESS
# =========================

@app.route("/order_success/<int:order_id>")
def order_success(order_id):

    return render_template(
        "order_success.html",
        order_id=order_id
    )


# =========================
# MY ORDERS
# =========================

@app.route("/orders")
def orders():

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM orders
        WHERE user_id = %s
        ORDER BY order_date DESC
        """,
        (
            session["user_id"],
        )
    )

    orders = cursor.fetchall()

    cursor.close()

    return render_template(
        "orders.html",
        orders=orders
    )


# =========================
# ORDER DETAILS
# =========================

@app.route("/order/<int:order_id>")
def order_details(order_id):

    if "user_id" not in session:

        return redirect(
            url_for("login")
        )

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM orders
        WHERE id = %s
        AND user_id = %s
        """,
        (
            order_id,
            session["user_id"]
        )
    )

    order = cursor.fetchone()

    if not order:

        cursor.close()

        return "Order not found!"

    cursor.execute(
        """
        SELECT
            order_items.quantity,
            order_items.price,
            food_items.name
        FROM order_items
        JOIN food_items
        ON order_items.food_id = food_items.id
        WHERE order_items.order_id = %s
        """,
        (order_id,)
    )

    items = cursor.fetchall()

    cursor.close()

    return render_template(
        "order_details.html",
        order=order,
        items=items
    )


# ==================================================
# ADMIN DASHBOARD
# ==================================================

@app.route("/admin")
def admin_dashboard():

    if not is_admin():

        return "Access Denied! Admins only."

    return render_template(
        "admin/dashboard.html"
    )


# ==================================================
# ADMIN FOOD MANAGEMENT
# ==================================================

@app.route("/admin/food")
def admin_food():

    if not is_admin():

        return "Access Denied! Admins only."

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT *
        FROM food_items
        ORDER BY id DESC
        """
    )

    foods = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/food.html",
        foods=foods
    )


# ==================================================
# ADD FOOD
# ==================================================

@app.route(
    "/admin/food/add",
    methods=["GET", "POST"]
)
def add_food():

    if not is_admin():

        return "Access Denied! Admins only."

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        category = request.form["category"]
        image = request.form["image"]

        available = 1

        if "available" not in request.form:

            available = 0

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO food_items
            (name, description, price, category, image, available)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                name,
                description,
                price,
                category,
                image,
                available
            )
        )

        db.commit()

        cursor.close()

        return redirect(
            url_for("admin_food")
        )

    return render_template(
        "admin/add_food.html"
    )


# ==================================================
# EDIT FOOD
# ==================================================

@app.route(
    "/admin/food/edit/<int:food_id>",
    methods=["GET", "POST"]
)
def edit_food(food_id):

    if not is_admin():

        return "Access Denied! Admins only."

    cursor = db.cursor(
        dictionary=True
    )

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        price = request.form["price"]
        category = request.form["category"]
        image = request.form["image"]

        available = 1

        if "available" not in request.form:

            available = 0

        cursor.execute(
            """
            UPDATE food_items
            SET
                name = %s,
                description = %s,
                price = %s,
                category = %s,
                image = %s,
                available = %s
            WHERE id = %s
            """,
            (
                name,
                description,
                price,
                category,
                image,
                available,
                food_id
            )
        )

        db.commit()

        cursor.close()

        return redirect(
            url_for("admin_food")
        )

    cursor.execute(
        """
        SELECT *
        FROM food_items
        WHERE id = %s
        """,
        (food_id,)
    )

    food = cursor.fetchone()

    cursor.close()

    if not food:

        return "Food item not found!"

    return render_template(
        "admin/edit_food.html",
        food=food
    )


# ==================================================
# DELETE FOOD
# ==================================================

@app.route(
    "/admin/food/delete/<int:food_id>",
    methods=["POST"]
)
def delete_food(food_id):

    if not is_admin():

        return "Access Denied! Admins only."

    cursor = db.cursor()

    cursor.execute(
        """
        DELETE FROM food_items
        WHERE id = %s
        """,
        (food_id,)
    )

    db.commit()

    cursor.close()

    return redirect(
        url_for("admin_food")
    )


# ==================================================
# ADMIN ORDER MANAGEMENT
# ==================================================

@app.route("/admin/orders")
def admin_orders():

    if not is_admin():

        return "Access Denied! Admins only."

    cursor = db.cursor(
        dictionary=True
    )

    cursor.execute(
        """
        SELECT
            orders.id,
            orders.total_amount,
            orders.status,
            orders.order_date,
            users.name,
            users.email
        FROM orders
        JOIN users
        ON orders.user_id = users.id
        ORDER BY orders.order_date DESC
        """
    )

    orders = cursor.fetchall()

    cursor.close()

    return render_template(
        "admin/orders.html",
        orders=orders
    )


# ==================================================
# UPDATE ORDER STATUS
# ==================================================

@app.route(
    "/admin/orders/update/<int:order_id>",
    methods=["POST"]
)
def update_order_status(order_id):

    if not is_admin():

        return "Access Denied! Admins only."

    status = request.form["status"]

    allowed_statuses = [
        "Pending",
        "Preparing",
        "Ready",
        "Delivered"
    ]

    if status not in allowed_statuses:

        return "Invalid order status!"

    cursor = db.cursor()

    cursor.execute(
        """
        UPDATE orders
        SET status = %s
        WHERE id = %s
        """,
        (
            status,
            order_id
        )
    )

    db.commit()

    cursor.close()

    return redirect(
        url_for("admin_orders")
    )


# =========================
# RUN APPLICATION
# =========================

if __name__ == "__main__":

    from waitress import serve

    port = int(os.getenv("PORT", "5000"))

    serve(
        app,
        host="0.0.0.0",
        port=port
    )