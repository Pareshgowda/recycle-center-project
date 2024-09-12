from flask import Flask, render_template, request, redirect, session as flask_session, flash, send_file
from database import session as db_session, User, WasteRecord, Category
import bcrypt
import datetime
import pandas as pd
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create Admin User if not present
def create_admin_user():
    admin = db_session.query(User).filter_by(username='admin').first()
    if not admin:
        hashed_password = bcrypt.hashpw('adminpassword'.encode('utf-8'), bcrypt.gensalt())
        admin_user = User(username='admin', password=hashed_password.decode('utf-8'), role='admin')
        db_session.add(admin_user)
        db_session.commit()

# Initialize the app by creating an admin user
create_admin_user()

# Route to display the login page
@app.route('/')
def home():
    return render_template('login.html')

# Route to handle login
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password'].encode('utf-8')

    # Query the database for the user
    user = db_session.query(User).filter_by(username=username).first()
    if user and bcrypt.checkpw(password, user.password.encode('utf-8')):
        flask_session['user_id'] = user.id
        flask_session['role'] = user.role
        return redirect('/log-waste')
    flash("Invalid credentials")
    return redirect('/')

# Route to log and update waste data
@app.route('/log-waste', methods=['GET', 'POST'])
def log_waste():
    if 'user_id' not in flask_session:
        return redirect('/')

    # Get today's waste data (if it exists)
    today = datetime.datetime.now().date()
    existing_record = db_session.query(WasteRecord).filter_by(user_id=flask_session['user_id'], date_collected=today).first()

    if request.method == 'POST':
        # Get data from the form
        data = request.form.to_dict()
        for field, value in data.items():
            if value == "":
                data[field] = None

        # Update existing data or insert new record
        if existing_record:
            # Update the existing record
            for key, value in data.items():
                setattr(existing_record, key, float(value) if value else None)
            flash("Waste data updated successfully!")
        else:
            # Create a new waste record
            waste_record = WasteRecord(
                date_collected=today,
                landfill_waste=float(data.get('landfill_waste', 0)),
                food_waste=float(data.get('food_waste', 0)),
                aluminum=float(data.get('aluminum', 0)),
                cardboard=float(data.get('cardboard', 0)),
                glass=float(data.get('glass', 0)),
                metal_cans=float(data.get('metal_cans', 0)),
                metal_scrap=float(data.get('metal_scrap', 0)),
                paper_books=float(data.get('paper_books', 0)),
                paper_mixed=float(data.get('paper_mixed', 0)),
                paper_newspaper=float(data.get('paper_newspaper', 0)),
                paper_white=float(data.get('paper_white', 0)),
                plastic_pet=float(data.get('plastic_pet', 0)),
                plastic_hdpe_colored=float(data.get('plastic_hdpe_colored', 0)),
                plastic_hdpe_natural=float(data.get('plastic_hdpe_natural', 0)),
                user_id=flask_session['user_id']
            )
            db_session.add(waste_record)
            flash("Waste data logged successfully!")
        
        db_session.commit()
        return redirect('/log-waste')

    return render_template('log_waste.html', record=existing_record)

# Route to manage users (only for admin)
@app.route('/manage-users', methods=['GET', 'POST'])
def manage_users():
    if 'user_id' not in flask_session or flask_session['role'] != 'admin':
        return redirect('/')

    users = db_session.query(User).all()

    if request.method == 'POST':
        if 'add_user' in request.form:
            username = request.form['username']
            password = request.form['password'].encode('utf-8')
            role = request.form['role']
            hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
            new_user = User(username=username, password=hashed_password.decode('utf-8'), role=role)
            db_session.add(new_user)
            db_session.commit()
            flash("User added successfully!")

        if 'delete_user' in request.form:
            user_id = request.form['user_id']
            user_to_delete = db_session.query(User).filter_by(id=user_id).first()
            if user_to_delete.username != 'admin':  # Prevent deleting the admin
                db_session.delete(user_to_delete)
                db_session.commit()
                flash("User deleted successfully!")

    return render_template('manage_users.html', users=users)

# Route to generate a report
@app.route('/generate-report', methods=['GET', 'POST'])
def generate_report():
    if 'user_id' not in flask_session or flask_session['role'] != 'admin':
        return redirect('/')

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        records = db_session.query(WasteRecord).filter(WasteRecord.date_collected.between(start_date, end_date)).all()

        data = [{
            'Date': record.date_collected,
            'Landfill Waste': record.landfill_waste,
            'Food Waste': record.food_waste,
            'Aluminum': record.aluminum,
            'Cardboard': record.cardboard,
            'Glass': record.glass,
            'Metal Cans': record.metal_cans,
            'Metal Scrap': record.metal_scrap,
            'Paper Books': record.paper_books,
            'Paper Mixed': record.paper_mixed,
            'Paper Newspaper': record.paper_newspaper,
            'Paper White': record.paper_white,
            'Plastic PET': record.plastic_pet,
            'Plastic HDPE Colored': record.plastic_hdpe_colored,
            'Plastic HDPE Natural': record.plastic_hdpe_natural,
        } for record in records]

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name="Waste_Report.xlsx")

    return render_template('generate_report.html')

# Route for user logout
@app.route('/logout')
def logout():
    flask_session.clear()  # Clear the Flask session
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
