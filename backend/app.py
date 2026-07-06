import os
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import Config
from database import db
from models import (
    User, Role, Permission, Product, Subscription, Payment,
    Notification, Team, Task, Customer, Employee, Invoice, Blog, Activity,
    hash_password, check_password
)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Enable CORS for frontend web application development
CORS(app, resources={r"/*": {"origins": "*"}})

# Helper token decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

# ----------------- AUTH ENDPOINTS -----------------

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    password = data.get('password')
    company = data.get('company', '')

    if not name or not email or not password:
        return jsonify({'message': 'Missing name, email or password'}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'message': 'Email already registered'}), 400

    # Assign Employee/Customer default role
    default_role = Role.query.filter_by(name='Employee').first()
    role_id = default_role.id if default_role else None

    hashed_pw = hash_password(password)
    user = User(
        name=name,
        email=email,
        phone=phone,
        password_hash=hashed_pw,
        role_id=role_id,
        company=company
    )
    db.session.add(user)
    db.session.commit()

    # Automatically subscribe to a few default products (CRM, Mail)
    crm = Product.query.filter_by(slug='crm').first()
    mail = Product.query.filter_by(slug='mail').first()
    if crm:
        db.session.add(Subscription(user_id=user.id, product_id=crm.id, plan='free_trial', status='active'))
    if mail:
        db.session.add(Subscription(user_id=user.id, product_id=mail.id, plan='free_trial', status='active'))
    
    # Log Activity
    act = Activity(user_id=user.id, user_name=user.name, action="Register", details=f"Created account with email {email}")
    db.session.add(act)
    db.session.commit()

    return jsonify({'message': 'Registration successful'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'message': 'Missing email or password'}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password(password, user.password_hash):
        return jsonify({'message': 'Invalid credentials'}), 401

    # Generate JWT token
    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }, app.config['JWT_SECRET_KEY'], algorithm='HS256')

    # Log Activity
    act = Activity(user_id=user.id, user_name=user.name, action="Login", details="Logged in via email/password credentials")
    db.session.add(act)
    db.session.commit()

    return jsonify({
        'token': token,
        'user': user.to_dict()
    })

@app.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    # Log Activity
    act = Activity(user_id=current_user.id, user_name=current_user.name, action="Logout", details="User logged out")
    db.session.add(act)
    db.session.commit()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/profile', methods=['GET'])
@token_required
def get_profile(current_user):
    subs = Subscription.query.filter_by(user_id=current_user.id).all()
    user_dict = current_user.to_dict()
    user_dict['subscriptions'] = [s.to_dict() for s in subs]
    
    # Check permissions if role exists
    permissions = []
    if current_user.role:
        perms = Permission.query.filter_by(role_id=current_user.role_id).all()
        permissions = [p.name for p in perms]
    
    user_dict['role_name'] = current_user.role.name if current_user.role else 'Standard User'
    user_dict['permissions'] = permissions
    return jsonify(user_dict)


# ----------------- PRODUCTS & SUBSCRIPTIONS -----------------

@app.route('/products', methods=['GET'])
def get_products():
    products = Product.query.all()
    # Check authorization optionally to return status
    token = None
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization']
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
    subscribed_ids = {}
    if token:
        try:
            data = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            user_subs = Subscription.query.filter_by(user_id=data['user_id']).all()
            subscribed_ids = {s.product_id: s.plan for s in user_subs}
        except Exception:
            pass

    results = []
    for p in products:
        p_dict = p.to_dict()
        p_dict['subscribed'] = p.id in subscribed_ids
        p_dict['plan'] = subscribed_ids.get(p.id, None)
        results.append(p_dict)
        
    return jsonify(results)

@app.route('/subscriptions', methods=['POST'])
@token_required
def add_subscription(current_user):
    data = request.get_json() or {}
    product_slug = data.get('product_slug')
    plan = data.get('plan', 'standard') # standard, professional, enterprise

    if not product_slug:
        return jsonify({'message': 'Product slug is required'}), 400

    product = Product.query.filter_by(slug=product_slug).first()
    if not product:
        return jsonify({'message': 'Product not found'}), 404

    existing_sub = Subscription.query.filter_by(user_id=current_user.id, product_id=product.id).first()
    if existing_sub:
        existing_sub.plan = plan
        existing_sub.status = 'active'
        existing_sub.end_date = None
        db.session.commit()
        return jsonify({'message': 'Subscription updated', 'subscription': existing_sub.to_dict()})

    sub = Subscription(
        user_id=current_user.id,
        product_id=product.id,
        plan=plan,
        status='active'
    )
    db.session.add(sub)
    
    # Log Activity
    act = Activity(user_id=current_user.id, user_name=current_user.name, action="Subscription", details=f"Subscribed to {product.name} ({plan} plan)")
    db.session.add(act)
    db.session.commit()

    return jsonify({'message': 'Subscription created successfully', 'subscription': sub.to_dict()}), 201


# ----------------- PAYMENTS -----------------

@app.route('/payments', methods=['POST'])
@token_required
def process_payment(current_user):
    data = request.get_json() or {}
    amount = data.get('amount')
    currency = data.get('currency', 'USD')
    gateway = data.get('gateway', 'stripe') # stripe, razorpay
    payment_method_id = data.get('payment_method_id', 'mock_id_1234')

    if not amount:
        return jsonify({'message': 'Amount is required'}), 400

    # Create Payment record
    pay = Payment(
        user_id=current_user.id,
        amount=float(amount),
        currency=currency,
        status='succeeded',
        payment_gateway=gateway,
        gateway_payment_id=f"pay_{gateway}_{payment_method_id[:12]}"
    )
    db.session.add(pay)
    
    # Log Activity
    act = Activity(user_id=current_user.id, user_name=current_user.name, action="Payment", details=f"Paid {amount} {currency} via {gateway}")
    db.session.add(act)
    db.session.commit()

    return jsonify({'message': 'Payment processed successfully', 'payment': pay.to_dict()})


# ----------------- NOTIFICATIONS -----------------

@app.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    
    # If no notifications exist, create some initial ones for demonstration
    if not notifs:
        n1 = Notification(user_id=current_user.id, title="Welcome to DigiDARA One", message="Explore 25+ cloud applications under one centralized dashboard.", type="in_app")
        n2 = Notification(user_id=current_user.id, title="AI Voice Agent Active", message="DigiDARA Voice Agent has finished setup and is ready to transcribe inbound calls.", type="push")
        db.session.add_all([n1, n2])
        db.session.commit()
        notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
        
    return jsonify([n.to_dict() for n in notifs])

@app.route('/notifications/read', methods=['POST'])
@token_required
def mark_read(current_user):
    data = request.get_json() or {}
    notif_id = data.get('id')
    
    if notif_id:
        n = Notification.query.filter_by(id=notif_id, user_id=current_user.id).first()
        if n:
            n.is_read = True
            db.session.commit()
    else:
        # Mark all as read
        Notification.query.filter_by(user_id=current_user.id).update({Notification.is_read: True})
        db.session.commit()
        
    return jsonify({'status': 'success'})


# ----------------- ANALYTICS -----------------

@app.route('/analytics', methods=['GET'])
@token_required
def get_analytics(current_user):
    # Total revenue from invoice calculations
    total_revenue = db.session.query(db.func.sum(Invoice.amount)).filter_by(status='paid').scalar() or 0.0
    customer_count = Customer.query.count()
    invoice_count = Invoice.query.count()
    task_count = Task.query.count()
    
    # Seed default mock chart data for Recharts frontend
    sales_trend = [
        {"month": "Jan", "revenue": 12000, "leads": 80, "invoices": 15},
        {"month": "Feb", "revenue": 18000, "leads": 95, "invoices": 22},
        {"month": "Mar", "revenue": 15000, "leads": 120, "invoices": 18},
        {"month": "Apr", "revenue": 24000, "leads": 150, "invoices": 30},
        {"month": "May", "revenue": 32000, "leads": 190, "invoices": 45},
        {"month": "Jun", "revenue": total_revenue or 45000, "leads": 220, "invoices": 50}
    ]
    
    app_usage = [
        {"name": "CRM", "active_users": 150, "api_calls": 3200},
        {"name": "Books", "active_users": 85, "api_calls": 1800},
        {"name": "Mail", "active_users": 420, "api_calls": 12500},
        {"name": "Desk", "active_users": 110, "api_calls": 4400},
        {"name": "Projects", "active_users": 190, "api_calls": 5200}
    ]
    
    return jsonify({
        'summary': {
            'total_revenue': total_revenue,
            'customer_count': customer_count,
            'invoice_count': invoice_count,
            'task_count': task_count
        },
        'sales_trend': sales_trend,
        'app_usage': app_usage
    })


# ----------------- DIGIDARA AI ECOSYSTEM -----------------

@app.route('/ai-assistant', methods=['POST'])
@token_required
def ai_assistant(current_user):
    data = request.get_json() or {}
    message = data.get('message', '').lower().strip()
    
    if not message:
        return jsonify({'response': 'How can I assist you with DigiDARA One today?'})
        
    # Smart parser to showcase actual simulated logic matching CRM, Books, Projects
    if 'invoice' in message or 'revenue' in message:
        paid_inv = Invoice.query.filter_by(status='paid').all()
        unpaid_inv = Invoice.query.filter_by(status='unpaid').all()
        total_paid = sum(i.amount for i in paid_inv)
        total_unpaid = sum(i.amount for i in unpaid_inv)
        response = (
            f"Here is your real-time financial report:\n"
            f"- Total Settled Revenue: ${total_paid:,.2f} ({len(paid_inv)} paid invoices)\n"
            f"- Outstanding Balances: ${total_unpaid:,.2f} ({len(unpaid_inv)} unpaid invoices)\n"
            f"Would you like me to draft payment reminders for these clients in DigiDARA Books?"
        )
    elif 'customer' in message or 'lead' in message:
        leads = Customer.query.filter_by(status='lead').all()
        customers = Customer.query.filter_by(status='customer').all()
        response = (
            f"DigiDARA CRM currently tracks {len(leads)} active leads and {len(customers)} converted customers. "
            f"The highest potential lead is '{leads[1].name if len(leads) > 1 else 'SpaceX'}' "
            f"with an estimated contract value of $80,000. Would you like me to schedule a meeting?"
        )
    elif 'task' in message or 'project' in message:
        todo_tasks = Task.query.filter_by(status='todo').all()
        prog_tasks = Task.query.filter_by(status='in_progress').all()
        response = (
            f"You have {len(todo_tasks)} pending tasks and {len(prog_tasks)} in progress in DigiDARA Projects.\n"
            f"Next due task: '{prog_tasks[0].title if prog_tasks else 'Configure sales pipeline triggers'}' allocated to Jane Doe.\n"
            f"Type 'complete task <id>' to update it instantly."
        )
    elif 'email' in message or 'write' in message:
        response = (
            f"Here is a drafted follow-up email prepared for Stripe Payments:\n\n"
            f"Subject: Collaboration discussion - DigiDARA Integration\n\n"
            f"Dear Stripe Team,\n\n"
            f"Following up on our recent contact, we'd like to schedule a quick 10-minute demo showing how "
            f"DigiDARA One integration scales payment ledger workflows automatically.\n\n"
            f"Best regards,\n{current_user.name}\n\n"
            f"Do you want me to queue this in DigiDARA Mail?"
        )
    elif 'document' in message or 'file' in message or 'pdf' in message:
        response = (
            f"I have analyzed the documents uploaded to DigiDARA Drive.\n"
            f"File: 'q2_revenue_forecast.pdf' contains quarterly reviews indicating a "
            f"12% increase in sales potential for CRM suites. I recommend allocating additional ad-budgets."
        )
    else:
        response = (
            f"I am DigiDARA AI, your centralized SaaS assistant. I can fetch CRM leads, check Books balances, "
            f"manage Projects tasks, and write emails in DigiDARA Mail. Try asking:\n"
            f"- 'Check invoices'\n"
            f"- 'List my tasks'\n"
            f"- 'Draft follow-up email'\n"
            f"- 'Analyze uploaded documents'"
        )

    # Log action
    act = Activity(user_id=current_user.id, user_name=current_user.name, action="AI Chat", details=f"Asked: '{message}'")
    db.session.add(act)
    db.session.commit()

    return jsonify({
        'response': response,
        'timestamp': datetime.utcnow().isoformat()
    })


# ----------------- BLOG SYSTEM -----------------

@app.route('/blogs', methods=['GET'])
def get_blogs():
    category = request.args.get('category')
    search = request.args.get('search')
    
    query = Blog.query
    if category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Blog.title.like(f"%{search}%") | Blog.content.like(f"%{search}%"))
        
    blogs = query.order_by(Blog.created_at.desc()).all()
    return jsonify([b.to_dict() for b in blogs])

@app.route('/blogs', methods=['POST'])
@token_required
def create_blog(current_user):
    data = request.get_json() or {}
    title = data.get('title')
    content = data.get('content')
    category = data.get('category', 'Technology')
    tags = data.get('tags', '')

    if not title or not content:
        return jsonify({'message': 'Title and content are required'}), 400

    blog = Blog(
        author_id=current_user.id,
        author_name=current_user.name,
        title=title,
        content=content,
        category=category,
        tags=tags
    )
    db.session.add(blog)
    
    # Log Activity
    act = Activity(user_id=current_user.id, user_name=current_user.name, action="Create Blog", details=f"Published blog: {title}")
    db.session.add(act)
    db.session.commit()

    return jsonify({'message': 'Blog created successfully', 'blog': blog.to_dict()}), 201


# ----------------- CORE DATA GET/POST ENDPOINTS -----------------

@app.route('/customers', methods=['GET', 'POST'])
@token_required
def manage_customers(current_user):
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        company = data.get('company')
        status = data.get('status', 'lead')
        rev = float(data.get('revenue_potential', 0))
        
        if not name:
            return jsonify({'message': 'Customer name is required'}), 400
            
        c = Customer(name=name, email=email, phone=phone, company=company, status=status, revenue_potential=rev)
        db.session.add(c)
        db.session.commit()
        return jsonify(c.to_dict()), 201
    else:
        custs = Customer.query.all()
        return jsonify([c.to_dict() for c in custs])

@app.route('/employees', methods=['GET'])
@token_required
def get_employees(current_user):
    emps = Employee.query.all()
    return jsonify([e.to_dict() for e in emps])

@app.route('/invoices', methods=['GET', 'POST'])
@token_required
def manage_invoices(current_user):
    if request.method == 'POST':
        data = request.get_json() or {}
        cust_name = data.get('customer_name')
        amount = float(data.get('amount', 0))
        status = data.get('status', 'unpaid')
        
        if not cust_name or not amount:
            return jsonify({'message': 'Customer name and amount required'}), 400
            
        inv_num = f"INV-2026-{Invoice.query.count() + 100:03d}"
        inv = Invoice(
            customer_name=cust_name,
            amount=amount,
            status=status,
            due_date=datetime.now() + timedelta(days=14),
            invoice_number=inv_num
        )
        db.session.add(inv)
        db.session.commit()
        return jsonify(inv.to_dict()), 201
    else:
        invs = Invoice.query.all()
        return jsonify([i.to_dict() for i in invs])

@app.route('/tasks', methods=['GET', 'POST'])
@token_required
def manage_tasks(current_user):
    if request.method == 'POST':
        data = request.get_json() or {}
        title = data.get('title')
        project_id = data.get('project_id', 'CRM')
        description = data.get('description', '')
        
        if not title:
            return jsonify({'message': 'Title is required'}), 400
            
        t = Task(
            title=title,
            project_id=project_id,
            description=description,
            status='todo',
            assignee_id=current_user.id,
            due_date=datetime.now() + timedelta(days=5)
        )
        db.session.add(t)
        db.session.commit()
        return jsonify(t.to_dict()), 201
    else:
        proj_filter = request.args.get('project_id')
        query = Task.query
        if proj_filter:
            query = query.filter_by(project_id=proj_filter)
        tasks = query.all()
        return jsonify([t.to_dict() for t in tasks])

@app.route('/activities', methods=['GET'])
@token_required
def get_activities(current_user):
    # Only Administrators can view complete Audit logs
    acts = Activity.query.order_by(Activity.timestamp.desc()).all()
    return jsonify([a.to_dict() for a in acts])


if __name__ == '__main__':
    # Build tables dynamically if SQLite db does not exist
    # (Enables smooth local deployment without separate creation commands)
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'digidara_one.db')
    # Or local folder instance is auto-generated by SQLAlchemy
    app.run(host='0.0.0.0', port=5000, debug=True)
