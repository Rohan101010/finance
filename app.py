import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime


from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    if "user_id" in session:
        user_id = session["user_id"]

    symbol_shares_price = db.execute("SELECT symbol,shares,price FROM stocks WHERE user_id = ?",user_id)
    total_value = 0
    for value in symbol_shares_price:
        total_value += int(value['shares']) * int(value['price'])

    cash = db.execute("SELECT cash FROM users WHERE id = ?",user_id)[0]["cash"]
    grand_total = int(total_value) + int(cash)

    aggregated_portfolio = {}
    for stock in symbol_shares_price:
        symbol = stock['symbol']
        shares = stock['shares']
        price = stock['price']
        if symbol in aggregated_portfolio:
            aggregated_portfolio[symbol]['shares'] += shares
            aggregated_portfolio[symbol]['total_cost'] += shares * price
        else:
            aggregated_portfolio[symbol] = {"symbol": symbol, "shares": shares, "total_cost": shares * price}

# Convert to list and calculate average price
    portfolio = []
    for symbol, data in aggregated_portfolio.items():
        if data['shares'] != 0:
            average_price = data['total_cost'] / data['shares']
            portfolio.append({"symbol": symbol, "shares": data['shares'], "price": average_price})
        else:
            average_price = 0

        


    return render_template("index.html", portfolio=portfolio,total_value=total_value, grand_total=grand_total, cash=cash)


@app.route("/", methods=["POST"])
@login_required
def add_cash():
    if 'myButton' in request.form:
        user_id = session["user_id"]
        cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)[0]["cash"]
        added_cash = float(request.form.get("added_cash"))
        db.execute("UPDATE users SET cash = ? WHERE id = ?", cash + added_cash, user_id)
    return redirect("/")






@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    #if method =get
        #show a form that allows users to buy a stock
        if request.method == "GET":
            return render_template("buy.html")

    #if POST
        if request.method == "POST":
            symbol_and_price = lookup(request.form.get("symbol"))
            if not symbol_and_price:
                 return apology("Stock does not exist", 400)


            shares = request.form.get("shares")
            if not shares:
                return apology ("Number of shares must be atleast 1", 400)
            else:
                try:
                    shares = int(shares)
                    if shares < 1:
                        return apology("must provide positive integer", 400)
                except ValueError:
                    return apology("must provide integer", 400)
                symbol = symbol_and_price["symbol"]
                price = symbol_and_price["price"]
                price = f"{price:2f}"
                value = float(price) * float(shares)


            if "user_id" in session:
                user_id = session["user_id"]
                username = db.execute("SELECT username FROM users WHERE id = ?",user_id)[0]["username"]


            cash = db.execute("SELECT cash FROM users WHERE username = ?",username)[0]["cash"]
            remainder = float(cash) - float(value)
            current_time = datetime.now()
            if value > cash:
                return apology("not enough cash in account")
            else:
                db.execute("INSERT INTO stocks(symbol,shares,price,date_of_purchase,user_id) VALUES(?,?,?,?,?)",symbol,shares,price,current_time,user_id)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", remainder, user_id)

            return redirect("/")



        # shares > 0
        # valid symbol
        #return apology
        # buy the stock id the user can afford it
        # create new tables in db
        # stock symbol, shares, price, date of purchase tables?
        # run SQL statement to purchase the stock
        # update the database and cash to reflect purchased stock



@app.route("/history")
@login_required
def history():
    user_id = session["user_id"]
    history = db.execute("SELECT symbol,shares,price,date_of_purchase FROM stocks WHERE user_id = ?",user_id)
    return render_template("history.html", history=history)



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    #show the html for quotes
    if request.method == "GET":
        return render_template("quote.html")

    if request.method == "POST":
        symbol1 = request.form.get("symbol")
        if symbol1:
            try:
                symbol_data = lookup(symbol1)
                print(symbol_data)  # Debugging line
                symbol2 = symbol_data["symbol"]
                price = symbol_data["price"]
                print(type(symbol_data["price"]))
                return render_template("quoted.html", symbol=symbol2, price=price)
            except:
                return apology("Stock does not exist", 400)

        else:
            return apology("must provide ticker",400)






@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not username or not password or not confirmation:
            return apology("No fields should be blank", 400)
        if password != confirmation:
            return apology("Password does not match confirmation", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", username)
        if len(rows) > 0:
            return apology("username already exists", 400)

        try:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, generate_password_hash(password))
        except ValueError:
            return apology("Invalid input",400)

        user_id = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
        session["user_id"] = user_id

        return redirect("/")

@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    #if GET display form which allows you to sell the stock
    if request.method == "GET":
        if "user_id" in session:
            user_id = session["user_id"]
        portfolio = db.execute("SELECT symbol FROM stocks WHERE user_id = ?", user_id)
        unique_portfolio = []
        seen_symbols = set()

        for stock in portfolio:
            if stock['symbol'] not in seen_symbols:
                unique_portfolio.append(stock)
                seen_symbols.add(stock['symbol'])
        return render_template("sell.html",portfolio=unique_portfolio)

    #If POST
    if request.method == "POST":
        user_id = session["user_id"]

        #access the form(stocks) make a variable
        stock = request.form.get("symbol")
        stocks_availible = [row["symbol"] for row in db.execute("SELECT symbol FROM stocks WHERE user_id = ?",user_id)]

        shares = int(request.form.get("shares"))
        result = db.execute("SELECT SUM(shares) AS total_shares FROM stocks WHERE symbol = ? AND user_id = ?", stock, user_id)
        shares_availible = int(result[0]["total_shares"])
        cash = db.execute("SELECT cash FROM users WHERE id = ?",user_id)[0]["cash"]
        cash = float(cash)
        quote = int(lookup(stock)["price"])
        value = float(quote * shares)
        current_time = datetime.now()

        if stock in stocks_availible:
            if 0 < shares <=shares_availible:
                db.execute("UPDATE users SET cash = ? WHERE id = ?", cash + value, user_id)
                db.execute("INSERT into stocks (user_id,symbol,shares, price, date_of_purchase) VALUES(?,?,?,?,?)", user_id, stock, -shares, quote, current_time )
            else:
                return apology("Invalid amount of shares")


        else:
            return apology("stock unavailible")


        return redirect("/")


        # if variable not in SQL table
            #return apology
        #access form no.shares
            #if < 0 or not in table
            #return
        #sell the shares
        #update the cash
        #update the database

