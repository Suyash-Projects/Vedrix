# Vedrix Security Guide

## Database Security Checklist

### ✅ Implemented Security Features

| Feature | Implementation | Status |
|---------|----------------|--------|
| SSL/TLS Encryption | PostgreSQL with `sslmode=require` | ✅ |
| Connection Pooling | SQLAlchemy with limits and timeouts | ✅ |
| SQL Injection Protection | Input validation and sanitization | ✅ |
| Field-level Encryption | Fernet encryption for sensitive data | ✅ |
| Password Hashing | bcrypt (already in use) | ✅ |
| Audit Logging | Database operation tracking | ✅ |
| Encrypted Backups | AES-256-CBC backup encryption | ✅ |
| Role-based Access | PostgreSQL users (app, readonly) | ✅ |

---

## Configuration

### Environment Variables

```bash
# Database with SSL (required for production)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DB_SSL_MODE=require  # Options: disable, require, verify-full

# Encryption key (auto-derived from SECRET_KEY)
SECRET_KEY=your-production-secret-key
```

### Connection Pool Settings

```python
# In app/db/session.py
pool_size=10          # Base connections
max_overflow=20       # Additional under load
pool_timeout=30       # Wait time
pool_recycle=1800     # Recycle after 30 min
pool_pre_ping=True   # Verify connection
```

---

## Security Layers

### 1. Network Layer
- SSL/TLS for database connections
- Firewall rules for PostgreSQL (port 5432)
- Private network for database server

### 2. Application Layer
- SQLAlchemy ORM prevents SQL injection
- Input validation via `InputValidator`
- Field encryption for PII (emails, phone numbers)
- JWT tokens with expiration

### 3. Database Layer
- Separate users with minimal privileges
- Row-level security (optional)
- Audit logging for all operations

### 4. Backup Security
- Encrypted backups with AES-256
- Separate encryption password
- Secure storage (not in repo)

---

## SQL Injection Prevention

### Input Validation
```python
from app.core.security_db import InputValidator, SQLInjectionGuard

# Validate user input
if not InputValidator.validate_email(email):
    raise ValueError("Invalid email")

# Check for dangerous SQL patterns
if SQLInjectionGuard.contains_dangerous_sql(user_input):
    raise ValueError("Invalid input")
```

### Safe Queries
Always use parameterized queries via SQLAlchemy:
```python
# ✅ Safe - uses parameterized query
result = await session.execute(
    select(User).where(User.email == email)
)

# ❌ Unsafe - string concatenation (never do this!)
query = f"SELECT * FROM users WHERE email = '{email}'"
```

---

## Field Encryption

### Encrypt Sensitive Data
```python
from app.core.encryption import FieldEncryption

# Encrypt before saving
encrypted_phone = FieldEncryption.encrypt(phone)

# Decrypt when reading
decrypted_phone = FieldEncryption.decrypt(encrypted_phone)
```

### Mask for Display
```python
from app.core.encryption import SensitiveDataMasker

masked_email = SensitiveDataMasker.mask_email("user@example.com")
# Result: us***@example.com
```

---

## Database Users

### Create Production Users
```bash
# Run on PostgreSQL server
psql -U postgres -d vedrix_prod -f Vedrix/scripts/postgres-init.sql
```

### User Roles
| User | Purpose | Permissions |
|------|---------|-------------|
| `vedrix_app` | Application | SELECT, INSERT, UPDATE, DELETE |
| `vedrix_readonly` | Analytics/Reports | SELECT only |

---

## Backup Security

### Encrypted Backup
```bash
# Create encrypted backup
./scripts/backup-encrypted.sh production true

# Decrypt and restore
openssl enc -aes-256-cbc -d -pbkdf2 -in backup.sql.enc -out backup.sql -pass file:backups/.backup_key
docker exec -i vedrix-db-prod pg_restore -U postgres -d vedrix_prod < backup.sql
```

---

## SSL/TLS Setup for PostgreSQL

### Generate Self-Signed Cert (testing)
```bash
# Generate certificate
openssl req -new -x509 -days 365 -nodes \
    -out server.crt -keyout server.key

# Copy to PostgreSQL data directory
cp server.crt server.key /var/lib/postgresql/data/
chown postgres:postgres /var/lib/postgresql/data/server.*
```

### Configure PostgreSQL (postgresql.conf)
```conf
ssl = on
ssl_cert_file = 'server.crt'
ssl_key_file = 'server.key'
ssl_prefer_server_ciphers = on
ssl_min_protocol_version = 'TLSv1.2'
```

---

## Security Monitoring

### View Audit Logs
```sql
SELECT * FROM audit_log
ORDER BY timestamp DESC
LIMIT 100;
```

### Check Failed Connections
```bash
# PostgreSQL logs
tail -f /var/log/postgresql/postgresql.log | grep "failed"
```

### Monitor Active Connections
```sql
SELECT count(*) as active_connections,
       state
FROM pg_stat_activity
WHERE datname = 'vedrix_prod'
GROUP BY state;
```

---

## Emergency Response

### If Database is Compromised
1. **Isolate**: Stop application immediately
2. **Assess**: Check which data was accessed
3. **Preserve**: Don't delete logs - they're evidence
4. **Notify**: Report to affected users
5. **Restore**: Wipe and restore from clean backup
6. **Patch**: Fix vulnerability before reconnecting

### Rotate Secrets
```bash
# Rotate all secrets immediately
1. SECRET_KEY (JWT)
2. DATABASE_PASSWORD
3. API keys (Groq, OpenRouter)
4. Redis password
```

---

## Compliance Notes

For production deployment, consider:
- [ ] GDPR compliance (data retention, deletion)
- [ ] SOC 2 controls
- [ ] Penetration testing
- [ ] Security audit
- [ ] DDoS protection
- [ ] WAF (Web Application Firewall)

---

## Contact

Security issues: security@vedrix.com