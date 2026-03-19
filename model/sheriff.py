"""Sheriff User model for the Deputy Sheriffs' Association of San Diego County."""
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
import json

from __init__ import app, db


class Sheriff(db.Model):
    """
    Sheriff Model

    Represents a deputy sheriff member in the DSA system.
    Stored in a separate 'sheriff_users' table in user_management.db.

    Attributes:
        id: Primary key
        _name: Full name of the sheriff
        _uid: Unique login username
        _sheriff_id: Badge/Sheriff ID number (e.g., "SD-4521")
        _email: Email address
        _password: Hashed password
        _rank: Rank (e.g., Deputy, Sergeant, Lieutenant, Captain)
        _station: Assigned station/location in San Diego County
        _phone: Contact phone number
        _role: Role in the system (Admin, Member)
        _status: Active, Retired, On Leave
    """
    __tablename__ = 'sheriff_users'

    id = db.Column(db.Integer, primary_key=True)
    _name = db.Column(db.String(255), unique=False, nullable=False)
    _uid = db.Column(db.String(255), unique=True, nullable=False)
    _sheriff_id = db.Column(db.String(50), unique=True, nullable=False)
    _email = db.Column(db.String(255), unique=False, nullable=False)
    _password = db.Column(db.String(255), unique=False, nullable=False)
    _rank = db.Column(db.String(100), default="Deputy", nullable=False)
    _station = db.Column(db.String(255), default="San Diego Central", nullable=False)
    _phone = db.Column(db.String(20), nullable=True)
    _role = db.Column(db.String(20), default="Member", nullable=False)
    _status = db.Column(db.String(20), default="Active", nullable=False)

    def __init__(self, name, uid, sheriff_id, password="sheriff123", email="",
                 rank="Deputy", station="San Diego Central", phone="",
                 role="Member", status="Active"):
        self._name = name
        self._uid = uid
        self._sheriff_id = sheriff_id
        self._email = email
        self.set_password(password)
        self._rank = rank
        self._station = station
        self._phone = phone
        self._role = role
        self._status = status

    # --- Properties ---
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def uid(self):
        return self._uid

    @uid.setter
    def uid(self, uid):
        self._uid = uid

    @property
    def sheriff_id(self):
        return self._sheriff_id

    @sheriff_id.setter
    def sheriff_id(self, sheriff_id):
        self._sheriff_id = sheriff_id

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, email):
        self._email = email

    @property
    def rank(self):
        return self._rank

    @rank.setter
    def rank(self, rank):
        self._rank = rank

    @property
    def station(self):
        return self._station

    @station.setter
    def station(self, station):
        self._station = station

    @property
    def phone(self):
        return self._phone

    @phone.setter
    def phone(self, phone):
        self._phone = phone

    @property
    def role(self):
        return self._role

    @role.setter
    def role(self, role):
        self._role = role

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, status):
        self._status = status

    @property
    def password(self):
        return self._password[0:10] + "..."

    def set_password(self, password):
        if password and password.startswith("pbkdf2:sha256:"):
            self._password = password
        else:
            self._password = generate_password_hash(password, "pbkdf2:sha256", salt_length=10)

    def is_password(self, password):
        return check_password_hash(self._password, password)

    def is_admin(self):
        return self._role == "Admin"

    def __str__(self):
        return json.dumps(self.read())

    # --- CRUD ---
    def create(self):
        try:
            db.session.add(self)
            db.session.commit()
            return self
        except IntegrityError:
            db.session.rollback()
            return None

    def read(self):
        return {
            "id": self.id,
            "name": self.name,
            "uid": self.uid,
            "sheriff_id": self.sheriff_id,
            "email": self.email,
            "rank": self.rank,
            "station": self.station,
            "phone": self.phone,
            "role": self.role,
            "status": self.status,
        }

    def update(self, inputs):
        if not isinstance(inputs, dict):
            return self
        if inputs.get("name"):
            self.name = inputs["name"]
        if inputs.get("email"):
            self.email = inputs["email"]
        if inputs.get("sheriff_id"):
            self.sheriff_id = inputs["sheriff_id"]
        if inputs.get("rank"):
            self.rank = inputs["rank"]
        if inputs.get("station"):
            self.station = inputs["station"]
        if inputs.get("phone"):
            self.phone = inputs["phone"]
        if inputs.get("role"):
            self.role = inputs["role"]
        if inputs.get("status"):
            self.status = inputs["status"]
        if inputs.get("password"):
            self.set_password(inputs["password"])
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return None
        return self

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        return None


def initSheriffs():
    """Create default sheriff users for testing."""
    with app.app_context():
        db.create_all()

        sheriffs = [
            Sheriff(
                name="DSA Admin",
                uid="dsa_admin",
                sheriff_id="SD-0001",
                password="SheriffAdmin123!",
                email="admin@dsasd.org",
                rank="Captain",
                station="DSA Headquarters - Poway",
                phone="(858) 486-9009",
                role="Admin",
                status="Active"
            ),
            Sheriff(
                name="Maria Rodriguez",
                uid="mrodriguez",
                sheriff_id="SD-2847",
                password="Deputy2847!",
                email="mrodriguez@sdsheriff.org",
                rank="Sergeant",
                station="Vista Station",
                phone="(760) 940-4551",
                role="Member",
                status="Active"
            ),
            Sheriff(
                name="James Thompson",
                uid="jthompson",
                sheriff_id="SD-3192",
                password="Deputy3192!",
                email="jthompson@sdsheriff.org",
                rank="Deputy",
                station="Rancho San Diego Station",
                phone="(619) 660-7090",
                role="Member",
                status="Active"
            ),
            Sheriff(
                name="David Chen",
                uid="dchen",
                sheriff_id="SD-1584",
                password="Deputy1584!",
                email="dchen@sdsheriff.org",
                rank="Lieutenant",
                station="San Marcos Station",
                phone="(760) 510-5200",
                role="Member",
                status="Active"
            ),
        ]

        for sheriff in sheriffs:
            try:
                sheriff.create()
            except IntegrityError:
                db.session.remove()
                print(f"Sheriff record exists or error: {sheriff.uid}")
