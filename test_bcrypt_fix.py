import bcrypt
import sys

print(f"Python Version: {sys.version}")
print(f"Bcrypt Version: {getattr(bcrypt, '__version__', 'N/A')}")

# Test the monkeypatch
class FakeBcryptAbout:
    __version__ = getattr(bcrypt, "__version__", "4.0.0")

if not hasattr(bcrypt, "__about__"):
    print("Applying monkeypatch...")
    bcrypt.__about__ = FakeBcryptAbout()

from passlib.context import CryptContext

try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    test_pass = "password123"
    hashed = pwd_context.hash(test_pass)
    print(f"Hashed: {hashed}")
    verified = pwd_context.verify(test_pass, hashed)
    print(f"Verified: {verified}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
