from flask import Flask
from config import Config
from database import db
from models import Role, User, Product, Subscription, Customer, Employee, Invoice, Blog, Task, Activity, hash_password
from datetime import datetime, timedelta

def seed_db():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    
    with app.app_context():
        print("Recreating database tables...")
        db.drop_all()
        db.create_all()
        
        print("Seeding Roles...")
        admin_role = Role(name='Administrator', description='System Admin with complete access')
        manager_role = Role(name='Manager', description='Team manager access')
        employee_role = Role(name='Employee', description='General staff access')
        customer_role = Role(name='Customer', description='Client access portal')
        
        db.session.add_all([admin_role, manager_role, employee_role, customer_role])
        db.session.commit()
        
        print("Seeding Users...")
        admin_user = User(
            name='DARA Administrator',
            email='admin@digidara.one',
            phone='+1-555-0199',
            password_hash=hash_password('adminpassword'),
            role_id=admin_role.id,
            company='DigiDARA HQ'
        )
        demo_user = User(
            name='Jane Doe',
            email='user@digidara.one',
            phone='+1-555-0100',
            password_hash=hash_password('userpassword'),
            role_id=employee_role.id,
            company='Acme Corp'
        )
        db.session.add_all([admin_user, demo_user])
        db.session.commit()
        
        print("Seeding Products...")
        product_list = [
            ("DigiDARA CRM", "crm", "Manage leads, sales pipelines, and customer engagements.", "Sales"),
            ("DigiDARA Books", "books", "Track expenses, raise invoices, and handle corporate tax.", "Finance"),
            ("DigiDARA Mail", "mail", "Enterprise-grade secure cloud email and communication suite.", "Email & Collaboration"),
            ("DigiDARA Desk", "desk", "Multi-channel support ticketing and customer service desk.", "Service"),
            ("DigiDARA Projects", "projects", "Plan projects, track tasks, and collaborate with your team.", "Project Management"),
            ("DigiDARA Analytics", "analytics", "Visual business intelligence, reports, and data dashboarding.", "Analytics"),
            ("DigiDARA People", "people", "Core HR, employee directory, leaves, and performance appraisals.", "Human Resources"),
            ("DigiDARA Inventory", "inventory", "Real-time stock tracking, purchase orders, and warehouse sync.", "Commerce"),
            ("DigiDARA Social Studio", "social", "Schedule posts, track mentions, and analyze social performance.", "Marketing"),
            ("DigiDARA Marketing Automation", "marketing", "Create multi-channel marketing campaigns and track conversions.", "Marketing"),
            ("DigiDARA Payroll", "payroll", "Automate salary calculations, tax deductions, and pay slips.", "Finance"),
            ("DigiDARA Recruit", "recruit", "Applicant tracking system (ATS) to streamline hiring pipelines.", "Human Resources"),
            ("DigiDARA ERP", "erp", "Integrated resources planning for enterprise inventory, sales, and manufacturing.", "ERP"),
            ("DigiDARA POS", "pos", "Cloud point-of-sale checkout system for brick-and-mortar retail.", "Commerce"),
            ("DigiDARA Commerce", "commerce", "Build customizable digital storefronts and manage e-commerce.", "Commerce"),
            ("DigiDARA Finance", "finance", "Advanced financial consolidation, budgeting, and audit reporting.", "Finance"),
            ("DigiDARA Voice Agent", "voice-agent", "AI-powered phone line customer assistant and automatic dialing.", "Developer Tools"),
            ("DigiDARA AI Chatbot", "chatbot", "Intelligent self-learning conversational customer agent.", "Developer Tools"),
            ("DigiDARA WhatsApp Automation", "whatsapp", "Bulk communications, order updates, and chat automation on WhatsApp.", "Email & Collaboration"),
            ("DigiDARA Calendar", "calendar", "Shared schedules, meeting reminders, and team availability views.", "Email & Collaboration"),
            ("DigiDARA Drive", "drive", "Secure cloud file explorer, documents management, and storage hub.", "Email & Collaboration"),
            ("DigiDARA Notes", "notes", "Rich-text sticky notes, check-lists, and thoughts catalog.", "Email & Collaboration"),
            ("DigiDARA Meetings", "meetings", "High-definition video conferencing and webinar portal.", "Email & Collaboration"),
            ("DigiDARA Forms", "forms", "Custom drag-and-drop form builder for lead capture and surveys.", "Marketing"),
            ("DigiDARA Survey", "survey", "Conduct customer satisfaction and employee opinion polls.", "Human Resources"),
            ("DigiDARA Creator", "creator", "Low-code app development platform for custom enterprise workflows.", "Developer Tools"),
            ("DigiDARA API Platform", "api", "Expose endpoints, manage webhook integrations, and API gateways.", "Developer Tools")
        ]
        
        db_products = []
        for name, slug, desc, cat in product_list:
            p = Product(name=name, slug=slug, description=desc, category=cat, try_count=12)
            db.session.add(p)
            db_products.append(p)
        db.session.commit()
        
        # Subscribe admin & demo user to some default products
        print("Seeding Subscriptions...")
        sub1 = Subscription(user_id=admin_user.id, product_id=db_products[0].id, plan='enterprise', status='active') # CRM
        sub2 = Subscription(user_id=admin_user.id, product_id=db_products[1].id, plan='enterprise', status='active') # Books
        sub3 = Subscription(user_id=admin_user.id, product_id=db_products[4].id, plan='enterprise', status='active') # Projects
        sub4 = Subscription(user_id=demo_user.id, product_id=db_products[0].id, plan='free_trial', status='active')
        sub5 = Subscription(user_id=demo_user.id, product_id=db_products[2].id, plan='standard', status='active') # Mail
        db.session.add_all([sub1, sub2, sub3, sub4, sub5])
        db.session.commit()
        
        print("Seeding Customers & Invoices...")
        c1 = Customer(user_id=demo_user.id, name="Tesla Inc.", email="billing@tesla.com", phone="+1-800-TESLA", company="Tesla Inc.", status="customer", revenue_potential=50000.00)
        c2 = Customer(name="SpaceX Ltd.", email="procurement@spacex.com", phone="+1-888-SPACEX", company="SpaceX", status="customer", revenue_potential=120000.00)
        c3 = Customer(name="Neuralink Co.", email="contact@neuralink.com", phone="+1-899-NEURA", company="Neuralink", status="lead", revenue_potential=15000.00)
        c4 = Customer(name="Stripe Payments", email="finance@stripe.com", phone="+1-555-STRIPE", company="Stripe", status="lead", revenue_potential=80000.00)
        db.session.add_all([c1, c2, c3, c4])
        db.session.commit()
        
        inv1 = Invoice(customer_id=c1.id, customer_name="Tesla Inc.", amount=4500.00, status="paid", due_date=datetime.now() - timedelta(days=2), invoice_number="INV-2026-001")
        inv2 = Invoice(customer_id=c2.id, customer_name="SpaceX Ltd.", amount=12000.00, status="unpaid", due_date=datetime.now() + timedelta(days=15), invoice_number="INV-2026-002")
        inv3 = Invoice(customer_id=c1.id, customer_name="Tesla Inc.", amount=3200.00, status="overdue", due_date=datetime.now() - timedelta(days=10), invoice_number="INV-2026-003")
        db.session.add_all([inv1, inv2, inv3])
        db.session.commit()
        
        print("Seeding Employees...")
        emp1 = Employee(user_id=demo_user.id, name="Jane Doe", department="Engineering", role="Software Engineer", salary=95000.00)
        emp2 = Employee(name="John Smith", department="Sales", role="Account Executive", salary=60000.00)
        emp3 = Employee(name="Robert Johnson", department="Support", role="Customer Support Specialist", salary=50000.00)
        db.session.add_all([emp1, emp2, emp3])
        db.session.commit()
        
        print("Seeding Project Tasks...")
        task1 = Task(project_id="CRM", title="Configure sales pipeline triggers", description="Set up automatic lead classification triggers on contact form submissions.", status="in_progress", assignee_id=demo_user.id, due_date=datetime.now() + timedelta(days=3))
        task2 = Task(project_id="CRM", title="Import client CSV list", description="Import legacy customer spreadsheets into the unified DigiDARA database.", status="done", assignee_id=admin_user.id, due_date=datetime.now() - timedelta(days=1))
        task3 = Task(project_id="Books", title="Reconcile bank statements", description="Verify incoming invoice settlements against payment processor deposits.", status="todo", assignee_id=demo_user.id, due_date=datetime.now() + timedelta(days=7))
        task4 = Task(project_id="Projects", title="Refactor design token CSS variables", description="Standardize light and dark mode glassmorphism styles across all sub-apps.", status="todo", assignee_id=admin_user.id, due_date=datetime.now() + timedelta(days=1))
        db.session.add_all([task1, task2, task3, task4])
        db.session.commit()
        
        print("Seeding Blogs...")
        blog1 = Blog(
            author_id=admin_user.id,
            author_name="DARA Admin",
            title="Introducing DigiDARA One: The Unified Enterprise OS",
            content="Welcome to the future of cloud computing. DigiDARA One unifies over 25+ essential products including CRM, Books, Mail, Desk, Projects, and Analytics under one single account, single dashboard, and single shared database. No more data silos. Discover how this simplifies management, improves team collaboration, and uses built-in AI assistant features.",
            category="Company News",
            tags="SaaS,Enterprise,DigiDARA,Cloud"
        )
        blog2 = Blog(
            author_id=admin_user.id,
            author_name="DARA Admin",
            title="How Generative AI is Redefining Customer Support Desk",
            content="Customer expectations have never been higher. With instant response times and hyper-personalized suggestions, standard ticketers are falling behind. DigiDARA Desk leverages DigiDARA AI to draft email replies, transcribe voice tickets, and offer automated self-service paths. In this blog post, we analyze stats showing how this reduces ticket volume by 45%.",
            category="Technology",
            tags="AI,CustomerSupport,Desk,Innovation"
        )
        db.session.add_all([blog1, blog2])
        db.session.commit()
        
        print("Seeding Activities...")
        act1 = Activity(user_id=admin_user.id, user_name="DARA Administrator", action="Login", details="Logged in from IP 192.168.1.55 (Chrome, Windows 11)")
        act2 = Activity(user_id=demo_user.id, user_name="Jane Doe", action="Subscription", details="Subscribed to DigiDARA Mail standard plan")
        act3 = Activity(user_id=admin_user.id, user_name="DARA Administrator", action="Database Seed", details="Database initial seeding completed successfully")
        db.session.add_all([act1, act2, act3])
        db.session.commit()
        
        print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_db()
