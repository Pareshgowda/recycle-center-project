from flask import Flask, render_template, request, redirect, session as flask_session, flash, send_file, url_for, jsonify
from database import session as db_session, User, WasteRecord, Category
import bcrypt
import datetime
import pandas as pd
from io import BytesIO
from dateutil.parser import parse
from sqlalchemy.orm import joinedload

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Create Admin User if not present (using a helper function)
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

  # Query the database for the user efficiently
  user = db_session.query(User).filter_by(username=username).first()
  if user and bcrypt.checkpw(password, user.password.encode('utf-8')):
    flask_session['user_id'] = user.id
    flask_session['role'] = user.role
    return redirect('/log-waste')
  flash("Invalid credentials")
  return redirect('/')

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
  
# Add this custom filter
@app.template_filter('get_attribute')
def get_attribute(obj, attr):
    return getattr(obj, attr, '')
  
# Route to log and update waste data
@app.route('/log-waste', methods=['GET', 'POST'])
def log_waste():
    if 'user_id' not in flask_session:
        return redirect('/')
    
    user_id = flask_session['user_id']
    
    if request.method == 'GET':
        selected_date = request.args.get('date_view') or flask_session.get('selected_date')
        if selected_date:
            selected_date = parse(selected_date).date()
            existing_record = db_session.query(WasteRecord).filter_by(user_id=user_id, date_collected=selected_date).first()
            
            flask_session['selected_date'] = selected_date.isoformat()
            
            categories = db_session.query(Category).filter_by(parent_id=None).options(joinedload(Category.children)).all()
            
            return render_template('log_waste.html', show_form=True, selected_date=selected_date, record=existing_record, categories=categories)
        else:
            return render_template('log_waste.html', show_form=False)
    
    elif request.method == 'POST':
        selected_date = parse(request.form['selected_date']).date()
        
        # Get data from the form
        data = {}
        for key, value in request.form.items():
            if key != 'selected_date':
                try:
                    data[key] = float(value) if value else 0
                except ValueError:
                    # Handle non-numeric values (e.g., for any text fields you might add in the future)
                    data[key] = value
        
        # Check for existing record
        existing_record = db_session.query(WasteRecord).filter_by(user_id=user_id, date_collected=selected_date).first()
        
        if existing_record:
            # Update existing record
            for key, value in data.items():
                setattr(existing_record, key, value)
            flash("Waste data updated successfully!")
        else:
            # Insert new record
            new_record = WasteRecord(date_collected=selected_date, user_id=user_id, **data)
            db_session.add(new_record)
            flash("Waste data created successfully!")
        
        db_session.commit()
        return redirect(url_for('log_waste', date_view=selected_date))
    
    return render_template('log_waste.html', show_form=False)

# Route to generate a report
@app.route('/generate-report', methods=['GET', 'POST'])
def generate_report():
    if 'user_id' not in flask_session or flask_session['role'] != 'admin':
        return redirect('/')

    if request.method == 'POST':
        start_date = request.form['start_date']
        end_date = request.form['end_date']

        # Query the database efficiently
        records = db_session.query(WasteRecord).filter(WasteRecord.date_collected.between(start_date, end_date)).all()

        # Create the DataFrame efficiently
        data = [{
            'Date': record.date_collected,
            'Food Compost': record.food_compost,
            'Food NonCompost': record.food_noncompost,
            'Cardboard': record.cardboard,
            'Paper Mixed': record.paper_mixed,
            'Paper Newspaper': record.paper_newspaper,
            'Paper White': record.paper_white,
            'Plastic Pet': record.plastic_pet,
            'Plastic Natural': record.plastic_natural,
            'Plastic Colored': record.plastic_colored,
            'Aluminum': record.aluminum,
            'Metal Other': record.metal_other,
            'Glass': record.glass
        } for record in records]

        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)

        output.seek(0)

        return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         as_attachment=True, download_name="Waste_Report.xlsx")

    return render_template('generate_report.html')

# Route to add new category
@app.route('/add-category', methods=['GET', 'POST'])
def add_category():
    if 'user_id' not in flask_session:
        return redirect('/')

    if request.method == 'POST':
        category_name = request.form.get('category_name')
        subcategories = request.form.getlist('subcategories[]')

        if category_name and subcategories:
            new_category = Category(name=category_name)
            db_session.add(new_category)
            db_session.flush()  # This assigns an ID to new_category

            for subcategory in subcategories:
                if subcategory:  # Only add non-empty subcategories
                    new_subcategory = Category(name=subcategory, parent_id=new_category.id)
                    db_session.add(new_subcategory)

            db_session.commit()
            flash("Category and subcategories added successfully!")
        
        # Redirect back to log-waste with the stored date
        return redirect(url_for('log_waste', date_view=flask_session.get('selected_date')))

    # For GET requests, just render the add_category template
    return render_template('add_category.html')

# New route for deleting categories
@app.route('/delete-category', methods=['GET', 'POST'])
def delete_category():
    if 'user_id' not in flask_session:
        return redirect('/')

    categories = db_session.query(Category).filter_by(parent_id=None).all()

    if request.method == 'POST':
        category_id = request.form.get('category_id')
        subcategory_id = request.form.get('subcategory_id')

        if subcategory_id:
            subcategory = db_session.query(Category).get(subcategory_id)
            if subcategory:
                db_session.delete(subcategory)
                db_session.commit()
                flash("Subcategory deleted successfully!")
            else:
                flash("Subcategory not found!")
        elif category_id:
            category = db_session.query(Category).get(category_id)
            if category:
                # Delete subcategories
                for subcategory in category.children:
                    db_session.delete(subcategory)
                
                # Delete the main category
                db_session.delete(category)
                db_session.commit()
                flash("Category and its subcategories deleted successfully!")
            else:
                flash("Category not found!")
        
        return redirect(url_for('log_waste', date_view=flask_session.get('selected_date')))

    return render_template('delete_category.html', categories=categories)

@app.route('/get-subcategories/<int:category_id>')
def get_subcategories(category_id):
    subcategories = db_session.query(Category).filter_by(parent_id=category_id).all()
    return jsonify([{'id': sub.id, 'name': sub.name} for sub in subcategories])

# Route for user logout
@app.route('/logout')
def logout():
    flask_session.clear()  # Clear the Flask session
    return redirect('/')
    
if __name__ == '__main__':
    app.run(debug=True)
