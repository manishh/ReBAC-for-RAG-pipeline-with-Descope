# API AUTHENTICATION SERVICE - TECHNICAL SPECIFICATIONS
**Version:** 2.1  
**Last Updated:** February 2026  
**Owner:** Engineering Team  
**Classification:** Internal - Engineering Team Only

---

## Overview

This document outlines the technical specifications for our OAuth 2.0 authentication service implementation. The service handles user authentication, authorization, and token management for all client applications.

## Architecture

### System Components

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Client    │─────▶│  Auth Server │─────▶│  Resource   │
│  Application│      │   (OAuth)    │      │   Server    │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ▼
                     ┌──────────────┐
                     │   Database   │
                     │  (PostgreSQL)│
                     └──────────────┘
```

### Technology Stack

- **Backend Framework:** Node.js 20.x with Express.js
- **Database:** PostgreSQL 15.3
- **Cache Layer:** Redis 7.2
- **Token Management:** JWT with RS256 signing
- **Rate Limiting:** Redis-backed sliding window algorithm

## Authentication Flow

### 1. Authorization Code Flow

**Endpoint:** `POST /oauth/authorize`

**Request Parameters:**
```json
{
  "client_id": "string (required)",
  "redirect_uri": "string (required)",
  "response_type": "code",
  "scope": "string (space-separated)",
  "state": "string (recommended)"
}
```

**Response:**
- Success: 302 redirect to `redirect_uri?code={auth_code}&state={state}`
- Error: 400 with error details

### 2. Token Exchange

**Endpoint:** `POST /oauth/token`

**Request Body:**
```json
{
  "grant_type": "authorization_code",
  "code": "string (required)",
  "client_id": "string (required)",
  "client_secret": "string (required)",
  "redirect_uri": "string (required)"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "refresh_token": "string",
  "scope": "read write"
}
```

## Security Specifications

### Token Configuration

| Parameter | Value | Notes |
|-----------|-------|-------|
| Access Token TTL | 1 hour | Configurable per client |
| Refresh Token TTL | 30 days | Single-use, rotation enabled |
| Token Algorithm | RS256 | 2048-bit RSA keys |
| Token Size | ~850 bytes | Average JWT size |

### Rate Limits

- **Token Generation:** 10 requests/minute per IP
- **Token Refresh:** 5 requests/minute per refresh token
- **Authorization:** 20 requests/minute per client_id

### Security Headers

All responses include:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'
```

## Database Schema

### Users Table
```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  last_login TIMESTAMP,
  status VARCHAR(20) DEFAULT 'active',
  INDEX idx_email (email)
);
```

### OAuth Clients Table
```sql
CREATE TABLE oauth_clients (
  client_id VARCHAR(64) PRIMARY KEY,
  client_secret_hash VARCHAR(255) NOT NULL,
  redirect_uris TEXT[] NOT NULL,
  allowed_scopes TEXT[] NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX idx_client_id (client_id)
);
```

### Tokens Table
```sql
CREATE TABLE tokens (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  client_id VARCHAR(64) REFERENCES oauth_clients(client_id),
  access_token_hash VARCHAR(255) UNIQUE NOT NULL,
  refresh_token_hash VARCHAR(255) UNIQUE,
  expires_at TIMESTAMP NOT NULL,
  scope TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  INDEX idx_access_token (access_token_hash),
  INDEX idx_refresh_token (refresh_token_hash)
);
```

## API Error Codes

| Code | Message | Description |
|------|---------|-------------|
| 400 | invalid_request | Missing or malformed parameters |
| 401 | invalid_client | Client authentication failed |
| 401 | invalid_grant | Authorization code expired/invalid |
| 403 | access_denied | User denied authorization |
| 429 | rate_limit_exceeded | Too many requests |
| 500 | server_error | Internal server error |

## Performance Requirements

- **Token Generation:** < 100ms (p95)
- **Token Validation:** < 50ms (p95)
- **Database Queries:** < 20ms (p95)
- **Uptime SLA:** 99.9%

## Deployment

### Environment Variables
```bash
DATABASE_URL=postgresql://user:pass@host:5432/authdb
REDIS_URL=redis://host:6379
JWT_PRIVATE_KEY_PATH=/secrets/jwt-private.pem
JWT_PUBLIC_KEY_PATH=/secrets/jwt-public.pem
LOG_LEVEL=info
PORT=3000
```

### Docker Configuration
```yaml
services:
  auth-service:
    image: auth-service:2.1
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
    depends_on:
      - postgres
      - redis
```

## Monitoring & Logging

### Key Metrics
- Token generation rate
- Token validation failures
- Database connection pool utilization
- Response latency (p50, p95, p99)
- Error rate by endpoint

### Log Format
```json
{
  "timestamp": "2026-02-19T10:30:00Z",
  "level": "info",
  "service": "auth-service",
  "event": "token_generated",
  "client_id": "abc123",
  "user_id": "uuid",
  "duration_ms": 87
}
```

## Future Enhancements

- PKCE support for mobile/SPA clients
- Multi-factor authentication integration
- Social login providers (Google, GitHub)
- Token introspection endpoint
- Device authorization flow

---

**Document Maintainers:**
- Lead Engineer: Bob Smith (bob@company.com)
- Security Review: Carol Johnson (carol@company.com)

**Change History:**
- v2.1 (Feb 2026): Added rate limiting specs
- v2.0 (Jan 2026): Major refactor with Redis caching
- v1.5 (Dec 2025): Initial OAuth 2.0 implementation
