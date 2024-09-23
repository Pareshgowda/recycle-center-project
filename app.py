from flask import Flask, render_template, request, redirect, session, flash
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database import Base, User, WasteRecord, Category
import datetime
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database setup
engine = create_engine('sqlite:///recycle_center.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
db_session = Session()

# Create admin user if not already present
def create_admin_user():
    admin = db_session.query(User).filter_by(username='admin').first()
    if not admin:
        hashed_password = bcrypt.hashpw('adminpassword'.encode('utf-8'), bcrypt.gensalt())
        admin_user = User(username='admin', password=hashed_password.decode('utf-8'), role='admin')
        db_session.add(admin_user)
        db_session.commit()
        print("Admin user created: Username: admin, Password: adminpassword")

# Initialize the app by creating an admin user
create_admin_user()

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password'].encode('utf-8')

    user = db_session.query(User).filter_by(username=username).first()
    if user and bcrypt.checkpw(password, user.password.encode('utf-8')):
        session['user_id'] = user.id
        session['role'] = user.role
        return redirect('/log-waste')
    flash("Invalid credentials")
    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Route to manage categories
# Additional route to manage categories (for admin)
@app.route('/manage-categories', methods=['GET', 'POST'])
def manage_categories():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect('/')
    
    if request.method == 'POST':
        # Add new category
        if request.form.get('add_category'):
            new_category = request.form['category_name']
            category = Category(name=new_category)
            db_session.add(category)
            db_session.commit()
            flash(f'Category "{new_category}" added successfully!')
        
        # Delete existing category
        if request.form.get('delete_category'):
            category_id = request.form['delete_category']
            category = db_session.query(Category).filter_by(id=category_id).first()
            if category:
                db_session.delete(category)
                db_session.commit()
                flash(f'Category "{category.name}" deleted successfully!')

    categories = db_session.query(Category).all()
    return render_template('manage_categories.html', categories=categories)


# Route to log waste data
@app.route('/log-waste', methods=['GET', 'POST'])
def log_waste():
    if 'user_id' not in session:
        return redirect('/')

    categories = db_session.query(Category).all()

    if request.method == 'POST':
        waste_data = {}
        for category in categories:
            waste_data[category.name] = request.form.get(category.name)

        waste_record = WasteRecord(user_id=session['user_id'], date_collected=datetime.datetime.now(), data=waste_data)
        db_session.add(waste_record)
        db_session.commit()
        flash('Waste data logged successfully!')
        return redirect('/log-waste')

    return render_template('log_waste.html', categories=categories)

# Route to view data by date
@app.route('/view-data', methods=['GET'])
def view_data():
    selected_date = request.args.get('date_view')
    categories = db_session.query(Category).all()

    waste_record = db_session.query(WasteRecord).filter_by(date_collected=selected_date).first()

    viewed_data = waste_record.data if waste_record else None

    return render_template('log_waste.html', categories=categories, viewed_data=viewed_data, viewed_date=selected_date)

if __name__ == '__main__':
    app.run(debug=True)
