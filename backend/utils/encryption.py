import bcrypt
import uuid

def hash_password(password):
    """Hash a password for storing."""
    # Generate a salt and hash the password
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

def check_password(plain_password, hashed_password):
    """Verify a stored password against one provided by user."""
    # Convert string to bytes if stored as string in DB
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    
    # Check password
    return bcrypt.checkpw(plain_password, hashed_password)

def generate_uid():
    """Generate a unique user ID."""
    return str(uuid.uuid4())