from flask import Flask, render_template, request, redirect, session
from config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'university_secret_key'

def recommend_universities(percentage, budget, city, program):
    # Database se SAARI matching program wali universities lo
    # Sirf city filter nahi — program aur percentage filter hai
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''SELECT * FROM universities 
                   WHERE program = %s 
                   AND fees <= %s
                   AND min_percentage <= %s''',
                   (program, budget, percentage))
    universities = cursor.fetchall()
    cursor.close()
    conn.close()

    scored_universities = []
    for uni in universities:
        score = 0

        # DSA Concept: Priority — selected city ko bonus score do
        if uni[2] == city:
            score += 100  # City match hone par bada bonus

        # Ranking ka score
        score += (10 - uni[5]) * 10

        # Budget bonus
        budget_left = int(budget) - uni[4]
        score += (budget_left / 10000)

        # Percentage bonus
        percentage_gap = float(percentage) - uni[6]
        score += percentage_gap * 2

        scored_universities.append({
            'id': uni[0],
            'name': uni[1],
            'city': uni[2],
            'program': uni[3],
            'fees': uni[4],
            'ranking': uni[5],
            'min_percentage': uni[6],
            'score': round(score, 2),
            'is_preferred': uni[2] == city  # Preferred city flag
        })

    # DSA: Sort by score descending
    scored_universities.sort(key=lambda x: x['score'], reverse=True)

    return scored_universities

@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Input Validation
        if not username or not email or not password:
            error = 'All fields are required!'
        elif len(password) < 6:
            error = 'Password must be at least 6 characters!'
        elif password != confirm_password:
            error = 'Passwords do not match!'
        else:
            hashed_password = generate_password_hash(password)
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute('INSERT INTO users (username, email, password) VALUES (%s, %s, %s)',
                               (username, email, hashed_password))
                conn.commit()
                cursor.close()
                conn.close()
                return redirect('/login')
            except Exception as e:
                error = 'Email already exists!'

    return render_template('register.html', error=error)
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Input Validation
        if not email or not password:
            error = 'All fields are required!'
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()

            if user and check_password_hash(user[3], password):
                session['user_id'] = user[0]
                session['username'] = user[1]
                session['role'] = user[4]
                if user[4] == 'admin':
                    return redirect('/admin')
                else:
                    return redirect('/dashboard')
            else:
                error = 'Invalid email or password!'

    return render_template('login.html', error=error)
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Check karo user login hai ya nahi
    if 'user_id' not in session:
        return redirect('/login')
    
    error = None
    
    if request.method == 'POST':
        percentage = request.form['percentage']
        preferred_city = request.form['preferred_city']
        budget = request.form['budget']
        desired_program = request.form['desired_program']
        
        # Input Validation
        if not percentage or not preferred_city or not budget or not desired_program:
            error = 'All fields are required!'
        elif float(percentage) < 0 or float(percentage) > 100:
            error = 'Percentage must be between 0 and 100!'
        elif int(budget) <= 0:
            error = 'Budget must be a positive number!'
        else:
            # Student profile database mein save karo
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''INSERT INTO student_profiles 
                           (user_id, percentage, preferred_city, budget, desired_program) 
                           VALUES (%s, %s, %s, %s, %s)''',
                           (session['user_id'], percentage, preferred_city, budget, desired_program))
            conn.commit()
            cursor.close()
            conn.close()
            return redirect(f'/results?city={preferred_city}&budget={budget}&program={desired_program}&percentage={percentage}')
    
    return render_template('dashboard.html', username=session['username'], error=error)

@app.route('/logout')
def logout():
    # Session clear karo — user logout
    session.clear()
    return redirect('/login')
 
@app.route('/results')
def results():
    # Check karo user login hai ya nahi
    if 'user_id' not in session:
        return redirect('/login')
    
    # URL se data lo
    city = request.args.get('city')
    budget = request.args.get('budget')
    program = request.args.get('program')
    percentage = request.args.get('percentage')
    
    # Recommendation function call karo
    universities = recommend_universities(percentage, budget, city, program)
    
    return render_template('results.html', 
                         universities=universities,
                         city=city,
                         budget=budget,
                         program=program,
                         percentage=percentage,
                         username=session['username'])

@app.route('/admin')
def admin():
    # Check karo user login hai aur admin hai
    if 'user_id' not in session:
        return redirect('/login')
    if session['role'] != 'admin':
        return redirect('/dashboard')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM universities ORDER BY name')
    universities = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('admin.html', 
                         universities=universities,
                         username=session['username'],
                         error=None,
                         success=None)

@app.route('/admin/add', methods=['POST'])
def admin_add():
    # Check karo admin hai
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    name = request.form['name']
    city = request.form['city']
    program = request.form['program']
    fees = request.form['fees']
    ranking = request.form['ranking']
    min_percentage = request.form['min_percentage']
    
    # Input Validation
    if not name or not city or not program or not fees or not ranking or not min_percentage:
        return redirect('/admin')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO universities 
                   (name, city, program, fees, ranking, min_percentage) 
                   VALUES (%s, %s, %s, %s, %s, %s)''',
                   (name, city, program, fees, ranking, min_percentage))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect('/admin')

@app.route('/admin/delete/<int:uni_id>')
def admin_delete(uni_id):
    # Check karo admin hai
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM universities WHERE id = %s', (uni_id,))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect('/admin')

@app.route('/admin/edit/<int:uni_id>')
def admin_edit(uni_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM universities WHERE id = %s', (uni_id,))
    uni = cursor.fetchone()
    cursor.close()
    conn.close()
    
    return render_template('admin_edit.html', uni=uni, username=session['username'])

@app.route('/admin/update/<int:uni_id>', methods=['POST'])
def admin_update(uni_id):
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/login')
    
    name = request.form['name']
    city = request.form['city']
    program = request.form['program']
    fees = request.form['fees']
    ranking = request.form['ranking']
    min_percentage = request.form['min_percentage']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''UPDATE universities 
                   SET name=%s, city=%s, program=%s, 
                   fees=%s, ranking=%s, min_percentage=%s 
                   WHERE id=%s''',
                   (name, city, program, fees, ranking, min_percentage, uni_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    return redirect('/admin')

if __name__ == '__main__':
    app.run(debug=True)