# src/chronicle_logger/time_provider.py

from datetime import datetime, timedelta

class TimeProvider:
    """
    Abstraction over time operations to allow easy mocking in tests.
    
    Default implementation uses real system time.
    Tests can inject a fake implementation with fixed or controllable time.
    """
    
    def now(self) -> datetime:
        """Return current datetime (like datetime.now())."""
        return datetime.now()
    
    def utcnow(self) -> datetime:
        """Return current UTC datetime (like datetime.utcnow())."""
        return datetime.utcnow()
    
    def timedelta(self, **kwargs) -> timedelta:
        """Create a timedelta object (like datetime.timedelta)."""
        return timedelta(**kwargs)
    
    def strftime(self, dt: datetime, format_str: str) -> str:
        """Format datetime to string (like dt.strftime)."""
        return dt.strftime(format_str)